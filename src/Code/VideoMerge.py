import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, 
    QListWidgetItem, QPushButton, QFrame, QFileDialog, 
    QMessageBox, QAbstractItemView, QListView, QApplication
)
from PyQt5.QtCore import Qt, QSize
from moviepy.editor import VideoFileClip, concatenate_videoclips

def merge_videos(video_paths, output_path):
    if not video_paths:
        return
    
    clips = []
    try:
        for path in video_paths:
            if not os.path.exists(path):
                continue
            
            try:
                clip = VideoFileClip(path)
                if clips:
                    target_size = clips[0].size
                    if clip.size[0] != target_size[0] or clip.size[1] != target_size[1]:
                        clip = clip.resize(newsize=target_size)
                    if clip.fps != clips[0].fps:
                        clip = clip.set_fps(clips[0].fps)
                clips.append(clip)
            except Exception as e:
                print(f"Error loading clip {path}: {e}")
                continue
        
        if not clips:
            return

        final_clip = concatenate_videoclips(clips, method="compose")
        
        try:
            final_clip.write_videofile(
                output_path, 
                codec="h264_qsv", 
                audio_codec="aac",
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                ffmpeg_params=["-global_quality", "23"]
            )
        except:
            final_clip.write_videofile(
                output_path, 
                codec="libx264", 
                audio_codec="aac", 
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                ffmpeg_params=["-crf", "23"]
            )
        
        for clip in clips:
            clip.close()
            
    except Exception as e:
        raise e

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
        self.timeline_title.setObjectName("timeline_title")
        #self.timeline_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00bcff;")
        self.main_layout.addWidget(self.timeline_title)
        
        self.timeline_list = QListWidget()
        self.timeline_list.setFlow(QListWidget.LeftToRight)
        self.timeline_list.setViewMode(QListWidget.IconMode)
        self.timeline_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.timeline_list.setDefaultDropAction(Qt.MoveAction)
        self.timeline_list.setMovement(QListView.Snap)
        self.timeline_list.setResizeMode(QListWidget.Adjust)
        self.timeline_list.setMinimumHeight(200)
        self.timeline_list.setIconSize(QSize(120, 70))
        self.timeline_list.setSpacing(15)
        self.main_layout.addWidget(self.timeline_list)

        self.mid_container = QHBoxLayout()
        self.mid_container.setSpacing(15)
        
        self.source_container = QVBoxLayout()
        self.source_label = QLabel()
        self.timeline_title.setObjectName("source_title")
        #self.source_label.setStyleSheet("font-weight: bold;")
        self.source_list = QListWidget()
        self.source_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.source_list.setDragEnabled(True)
        
        self.source_container.addWidget(self.source_label)
        self.source_container.addWidget(self.source_list)
        
        self.mid_container.addLayout(self.source_container, 8)

        self.btn_panel = QVBoxLayout()
        self.btn_panel.setAlignment(Qt.AlignTop)
        self.btn_panel.setSpacing(10)
        
        self.btn_add = QPushButton()
        self.btn_to_timeline = QPushButton()
        self.btn_remove = QPushButton()
        self.btn_clear = QPushButton()
        
        self.buttons = [self.btn_add, self.btn_to_timeline, self.btn_remove, self.btn_clear]
        for btn in self.buttons:
            btn.setFixedWidth(130)
            btn.setFixedHeight(38)
            btn.setCursor(Qt.PointingHandCursor)
            self.btn_panel.addWidget(btn)
            
        self.mid_container.addLayout(self.btn_panel, 2)
        self.main_layout.addLayout(self.mid_container)

        self.line_sep = QFrame()
        self.line_sep.setFrameShape(QFrame.HLine)
        self.line_sep.setFrameShadow(QFrame.Sunken)
        #self.line_sep.setStyleSheet("background-color: #333;")
        self.main_layout.addWidget(self.line_sep)

        self.btn_run = QPushButton()
        self.btn_run.setFixedHeight(55)
        self.btn_run.setCursor(Qt.PointingHandCursor)
        self.main_layout.addWidget(self.btn_run)

        self.setLayout(self.main_layout)

        self.btn_add.clicked.connect(self.import_videos)
        self.btn_to_timeline.clicked.connect(self.add_to_timeline)
        self.btn_remove.clicked.connect(self.remove_from_timeline)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_run.clicked.connect(self.run_video_merge)

    def import_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 'Select Media', '', 'Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv *.webm)'
        )
        if files:
            for f in files:
                self.source_list.addItem(f)

    def add_to_timeline(self):
        selected = self.source_list.selectedItems()
        if not selected:
            return
        for item in selected:
            path = item.text()
            name = os.path.basename(path)
            list_item = QListWidgetItem(name)
            list_item.setData(Qt.UserRole, path)
            list_item.setTextAlignment(Qt.AlignCenter)
            list_item.setSizeHint(QSize(140, 90))
            self.timeline_list.addItem(list_item)

    def remove_from_timeline(self):
        items = self.timeline_list.selectedItems()
        if not items:
            return
        for item in items:
            self.timeline_list.takeItem(self.timeline_list.row(item))

    def clear_all(self):
        if self.timeline_list.count() == 0:
            return
        reply = QMessageBox.question(
            self, 'Confirm', 'Clear all items in timeline?', 
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.timeline_list.clear()

    def run_video_merge(self):
        count = self.timeline_list.count()
        if count < 2:
            QMessageBox.warning(self, "Warning", self.main_app.t('error_min_videos'))
            return
        
        video_paths = []
        for i in range(count):
            video_paths.append(self.timeline_list.item(i).data(Qt.UserRole))
            
        save_path, _ = QFileDialog.getSaveFileName(
            self, 'Save Merged Video', 'final_output.mp4', 'Video (*.mp4)'
        )
        
        if save_path:
            self.btn_run.setEnabled(False)
            self.btn_run.setText("Processing...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                merge_videos(video_paths, save_path)
                QMessageBox.information(self, "Success", self.main_app.t('success_merge'))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failure: {str(e)}")
            finally:
                self.btn_run.setEnabled(True)
                self.btn_run.setText(self.main_app.t('export_video'))
                QApplication.restoreOverrideCursor()