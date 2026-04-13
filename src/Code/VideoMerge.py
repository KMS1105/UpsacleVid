import os
import subprocess
import platform
import shutil
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QListWidgetItem, QPushButton, QFrame, QFileDialog, 
    QMessageBox, QAbstractItemView, QListView, QApplication, QTextEdit
)
from PyQt5.QtCore import Qt, QSize

def find_ffmpeg_bin(search_root):
    for root, dirs, files in os.walk(search_root):
        if "ffmpeg.exe" in files:
            full_path = os.path.join(root, "ffmpeg.exe")
            if "bin" in root.lower():
                return full_path
    return None

def merge_videos(video_paths, output_path, log_callback=None):
    if not video_paths: return
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir)
    ffmpeg_search_root = os.path.join(base_dir, "ffmpeg")
    
    ffmpeg_exe = find_ffmpeg_bin(ffmpeg_search_root)
    
    if not ffmpeg_exe or not os.path.exists(ffmpeg_exe):
        ffmpeg_exe = shutil.which("ffmpeg")
        if not ffmpeg_exe:
            raise Exception("FFmpeg 실행 파일을 찾을 수 없습니다.")

    list_path = os.path.join(current_dir, "merge_list.txt")
    
    try:
        if log_callback: log_callback(f"📝 {len(video_paths)}개 파일 병합 준비 중...")
        
        with open(list_path, 'w', encoding='utf-8') as f:
            for path in video_paths:
                abs_p = os.path.abspath(path)
                safe_p = abs_p.replace(os.sep, '/')
                f.write(f"file '{safe_p}'\n")

        if log_callback: log_callback("🚀 오디오 호환성 모드로 병합 시작...")
        
        cmd = [
            ffmpeg_exe, '-y', '-f', 'concat', '-safe', '0', '-i', list_path,
            '-c:v', 'copy',      
            '-c:a', 'aac',       
            '-b:a', '192k',     
            '-movflags', '+faststart', 
            output_path
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            shell=(platform.system() == 'Windows'),
            cwd=current_dir,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode != 0:
            raise Exception(result.stderr)
        if log_callback: log_callback(f"✅ 완료: {os.path.basename(output_path)}")
            
    finally:
        if os.path.exists(list_path):
            try: os.remove(list_path)
            except: pass

class VideoMergeTab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.initUI()

    def initUI(self):
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(15)

        self.timeline_title = QLabel()
        self.main_layout.addWidget(self.timeline_title)
        
        self.timeline_list = QListWidget()
        self.timeline_list.setFlow(QListWidget.LeftToRight)
        self.timeline_list.setViewMode(QListWidget.IconMode)
        self.timeline_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.timeline_list.setDefaultDropAction(Qt.MoveAction)
        self.timeline_list.setMovement(QListView.Snap)
        self.timeline_list.setResizeMode(QListWidget.Adjust)
        self.timeline_list.setMinimumHeight(180)
        self.timeline_list.setIconSize(QSize(120, 70))
        self.timeline_list.setSpacing(15)
        self.main_layout.addWidget(self.timeline_list)

        self.mid_container = QHBoxLayout()
        self.source_container = QVBoxLayout()
        self.source_label = QLabel()
        self.source_list = QListWidget()
        self.source_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.source_container.addWidget(self.source_label)
        self.source_container.addWidget(self.source_list)
        self.mid_container.addLayout(self.source_container, 8)

        self.btn_panel = QVBoxLayout()
        self.btn_panel.setAlignment(Qt.AlignTop)
        self.btn_add = QPushButton()
        self.btn_to_timeline = QPushButton()
        self.btn_remove = QPushButton()
        self.btn_clear = QPushButton()
        
        for btn in [self.btn_add, self.btn_to_timeline, self.btn_remove, self.btn_clear]:
            btn.setFixedWidth(130)
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            self.btn_panel.addWidget(btn)
        self.mid_container.addLayout(self.btn_panel, 2)
        self.main_layout.addLayout(self.mid_container)

        self.merge_log = QTextEdit()
        self.merge_log.setReadOnly(True)
        self.merge_log.setMaximumHeight(100)
        self.main_layout.addWidget(self.merge_log)

        self.btn_run = QPushButton()
        self.btn_run.setFixedHeight(50)
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.btn_run.setStyleSheet("background-color: #28a745; color: white; font-weight: bold;")
        self.main_layout.addWidget(self.btn_run)

        self.setLayout(self.main_layout)

        self.btn_add.clicked.connect(self.import_videos)
        self.btn_to_timeline.clicked.connect(self.add_to_timeline)
        self.btn_remove.clicked.connect(self.remove_from_timeline)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_run.clicked.connect(self.run_video_merge)

    def import_videos(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Media', '', 'Video Files (*.mp4 *.avi *.mkv *.mov *.webm)')
        if files:
            for f in files:
                self.source_list.addItem(f)
                self.merge_log.append(f"➕ 소스 추가: {os.path.basename(f)}")

    def add_to_timeline(self):
        selected = self.source_list.selectedItems()
        if not selected: return
        for item in selected:
            path = item.text()
            name = os.path.basename(path)
            list_item = QListWidgetItem(name)
            list_item.setData(Qt.UserRole, path)
            list_item.setTextAlignment(Qt.AlignCenter)
            list_item.setSizeHint(QSize(140, 90))
            self.timeline_list.addItem(list_item)
            self.merge_log.append(f"📥 타임라인 등록: {name}")

    def remove_from_timeline(self):
        items = self.timeline_list.selectedItems()
        if not items: return
        for item in items:
            self.merge_log.append(f"➖ 타임라인 제거: {item.text()}")
            self.timeline_list.takeItem(self.timeline_list.row(item))

    def clear_all(self):
        if self.timeline_list.count() == 0: return
        self.timeline_list.clear()
        self.merge_log.append("🧹 타임라인 초기화 완료")

    def run_video_merge(self):
        count = self.timeline_list.count()
        if count < 2:
            QMessageBox.warning(self, "Warning", self.main_app.t('error_min_videos'))
            return
        
        video_paths = [self.timeline_list.item(i).data(Qt.UserRole) for i in range(count)]
        save_path, _ = QFileDialog.getSaveFileName(self, 'Save Merged Video', 'merged.mp4', 'Video (*.mp4)')
        
        if save_path:
            self.btn_run.setEnabled(False)
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                merge_videos(video_paths, save_path, log_callback=self.merge_log.append)
                QMessageBox.information(self, "Success", self.main_app.t('success_merge'))
            except Exception as e:
                self.merge_log.append(f"❌ 오류: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failure: {str(e)}")
            finally:
                self.btn_run.setEnabled(True)
                QApplication.restoreOverrideCursor()