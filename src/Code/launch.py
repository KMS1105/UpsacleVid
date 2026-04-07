import os
import sys
import re

# DLL 경로 설정 (PyTorch 관련)
dll_path = os.path.join(sys.prefix, 'Lib', 'site-packages', 'torch', 'lib')
if os.path.exists(dll_path):
    os.add_dll_directory(dll_path)

from PyQt5.QtWidgets import (QApplication, QWidget, QTabWidget, QVBoxLayout, 
                             QMenuBar, QFileDialog, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QAbstractItemView, 
                             QMessageBox, QSlider, QFrame, QListView)
from PyQt5.QtCore import Qt, QSize

from setting import UI_TEXTS, get_device_info_text, get_device_recommendation, apply_app_theme
from UpscaleImg import create_image_tab, ImageUpscaleWorker
from UpscaleVid import create_video_tab, VideoUpscaleWorker

# 영상 합치기 로직
from moviepy.editor import VideoFileClip, concatenate_videoclips

def merge_videos(video_paths, output_path, quality=23):
    if not video_paths:
        return
    
    clips = []
    try:
        for path in video_paths:
            clip = VideoFileClip(path)
            if clips and (clip.size != clips[0].size):
                clip = clip.resize(width=clips[0].size[0], height=clips[0].size[1])
            clips.append(clip)
        
        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", ffmpeg_params=["-crf", str(quality)])
        
        for clip in clips:
            clip.close()
            
    except Exception as e:
        raise e

# 편집기 스타일의 영상 합치기 탭 클래스
class VideoMergeTab(QWidget):
    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # 1. 상단 타임라인 (드래그로 순서 변경 가능)
        self.timeline_title = QLabel()
        layout.addWidget(self.timeline_title)
        
        self.timeline_list = QListWidget()
        self.timeline_list.setFlow(QListWidget.LeftToRight) 
        self.timeline_list.setViewMode(QListWidget.IconMode) 
        self.timeline_list.setDragDropMode(QAbstractItemView.InternalMove) # 타임라인 내에서만 이동 가능
        self.timeline_list.setMovement(QListView.Snap)
        self.timeline_list.setResizeMode(QListWidget.Adjust)
        self.timeline_list.setIconSize(QSize(100, 60))
        self.timeline_list.setMinimumHeight(160)
        self.timeline_list.setSpacing(10)
        self.timeline_list.setStyleSheet("""
            QListWidget { 
                background-color: #1e1e1e; 
                border-radius: 10px; 
                border: 2px dashed #333; 
                padding: 10px;
            }
            QListWidget::item { 
                background-color: #3d5afe; 
                color: white; 
                border-radius: 5px;
                margin-right: 5px;
            }
            QListWidget::item:selected { border: 2px solid #ffffff; }
        """)
        layout.addWidget(self.timeline_list)

        # 2. 하단 소스 리스트 (고정 보관소)
        mid_layout = QHBoxLayout()
        
        list_container = QVBoxLayout()
        self.source_list = QListWidget()
        self.source_list.setDragEnabled(False) # 소스 리스트는 순서 고정
        self.source_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.source_list.setStyleSheet("QListWidget { background-color: #2d2d2d; color: #ccc; }")
        
        self.source_label = QLabel()
        list_container.addWidget(self.source_label)
        list_container.addWidget(self.source_list)
        mid_layout.addLayout(list_container, 7)

        # 사이드 컨트롤 버튼
        side_btn_layout = QVBoxLayout()
        side_btn_layout.setAlignment(Qt.AlignTop)
        
        self.btn_add = QPushButton() 
        self.btn_to_timeline = QPushButton() 
        self.btn_remove = QPushButton() 
        self.btn_clear = QPushButton() 
        
        self.btn_to_timeline.setStyleSheet("background-color: #3d5afe; color: white; font-weight: bold;")
        
        for btn in [self.btn_add, self.btn_to_timeline, self.btn_remove, self.btn_clear]:
            btn.setFixedWidth(110)
            side_btn_layout.addWidget(btn)
        
        mid_layout.addLayout(side_btn_layout, 1)
        layout.addLayout(mid_layout)

        # 3. 인코딩 설정 및 실행
        bottom_layout = QHBoxLayout()
        settings_group = QVBoxLayout()
        self.quality_label = QLabel()
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(18, 32)
        self.quality_slider.setValue(23)
        settings_group.addWidget(self.quality_label)
        settings_group.addWidget(self.quality_slider)
        bottom_layout.addLayout(settings_group, 4)

        self.btn_run = QPushButton()
        self.btn_run.setFixedHeight(50)
        self.btn_run.setProperty("class", "run-button")
        bottom_layout.addWidget(self.btn_run, 6)
        
        layout.addLayout(bottom_layout)
        self.setLayout(layout)

        # 이벤트 연결
        self.btn_add.clicked.connect(self.import_videos)
        self.btn_to_timeline.clicked.connect(self.add_to_timeline)
        self.btn_remove.clicked.connect(self.remove_from_timeline)
        self.btn_clear.clicked.connect(self.timeline_list.clear)
        self.btn_run.clicked.connect(self.run_video_merge)

    def import_videos(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select Videos', '', 'Videos (*.mp4 *.mov *.avi *.mkv)')
        if files:
            self.source_list.addItems(files)

    def add_to_timeline(self):
        selected_items = self.source_list.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            file_path = item.text()
            file_name = os.path.basename(file_path)
            new_item = QListWidgetItem(file_name)
            new_item.setToolTip(file_path)
            new_item.setData(Qt.UserRole, file_path) # 실제 경로 저장
            new_item.setTextAlignment(Qt.AlignCenter)
            new_item.setSizeHint(QSize(120, 80))
            self.timeline_list.addItem(new_item)

    def remove_from_timeline(self):
        for item in self.timeline_list.selectedItems():
            self.timeline_list.takeItem(self.timeline_list.row(item))

    def run_video_merge(self):
        count = self.timeline_list.count()
        if count < 2:
            QMessageBox.warning(self, "Warning", self.main_app.t('error_min_videos'))
            return

        video_paths = [self.timeline_list.item(i).data(Qt.UserRole) for i in range(count)]
        save_path, _ = QFileDialog.getSaveFileName(self, 'Export Video', 'merged_video.mp4', 'Video (*.mp4)')
        if save_path:
            try:
                quality_val = self.quality_slider.value()
                merge_videos(video_paths, save_path, quality_val)
                QMessageBox.information(self, "Success", self.main_app.t('success_merge'))
            except Exception as e:
                QMessageBox.critical(self, "Error", f"{str(e)}")

class UpscaleApp(QWidget):
    def __init__(self):
        super().__init__()
        self.language = 'ko'
        self.theme = 'light'
        self.ui_texts = UI_TEXTS
        self.translations = []
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Upscaler')
        self.setGeometry(120, 120, 780, 700) 
        self.menu_bar = QMenuBar()
        main_layout = QVBoxLayout()
        main_layout.setMenuBar(self.menu_bar)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(create_image_tab(self, self.translations), self.t('tab_image'))
        self.tabs.addTab(create_video_tab(self, self.translations), self.t('tab_video'))
        
        self.video_merge_tab = VideoMergeTab(self)
        self.tabs.addTab(self.video_merge_tab, self.t('tab_video_merge'))
        
        main_layout.addWidget(self.tabs)
        self.set_menu()
        self.setLayout(main_layout)
        self.set_theme(self.theme)
        self.update_language()

    def t(self, key):
        return self.ui_texts[self.language].get(key, key)

    def set_menu(self):
        self.menu_bar.clear()
        theme_menu = self.menu_bar.addMenu(self.t('menu_theme'))
        theme_menu.addAction(self.t('menu_light'), lambda: self.set_theme('light'))
        theme_menu.addAction(self.t('menu_dark'), lambda: self.set_theme('dark'))
        lang_menu = self.menu_bar.addMenu(self.t('menu_language'))
        lang_menu.addAction(self.t('lang_ko'), lambda: self.set_language('ko'))
        lang_menu.addAction(self.t('lang_en'), lambda: self.set_language('en'))

    def set_theme(self, theme):
        self.theme = theme
        apply_app_theme(self, theme)

    def set_language(self, language):
        self.language = language
        self.update_language()

    def update_language(self):
        self.setWindowTitle(self.t('window_title'))
        self.set_menu()
        self.tabs.setTabText(0, self.t('tab_image'))
        self.tabs.setTabText(1, self.t('tab_video'))
        self.tabs.setTabText(2, self.t('tab_video_merge'))
        
        for widget, method, key in self.translations:
            getattr(widget, method)(self.t(key))
            
        self.img_device_label.setText(get_device_info_text(self.language))
        self.vid_device_label.setText(get_device_info_text(self.language))
        self.img_recommend_label.setText(get_device_recommendation(self.language))
        self.vid_recommend_label.setText(get_device_recommendation(self.language))
        
        # 버튼/라벨 텍스트 갱신 (합치기 탭 포함)
        self.img_run_btn.setText(self.t('upscale_image'))
        self.vid_run_btn.setText(self.t('run_video_upscale'))
        
        m_tab = self.video_merge_tab
        m_tab.timeline_title.setText("🎬 " + self.t('video_timeline'))
        m_tab.source_label.setText("📂 " + self.t('video_sources'))
        m_tab.btn_add.setText("➕ " + self.t('add'))
        m_tab.btn_to_timeline.setText("⬇ " + self.t('add_to_timeline')) # setting.py에 추가 필요
        m_tab.btn_remove.setText("❌ " + self.t('remove'))
        m_tab.btn_clear.setText("🧹 " + self.t('clear'))
        m_tab.quality_label.setText(self.t('merge_quality'))
        m_tab.btn_run.setText("🚀 " + self.t('export_video'))
        
        for btn in [self.img_browse_btn, self.img_output_browse_btn, 
                    self.vid_browse_btn, self.output_browse_btn]:
            btn.setText(self.t('browse'))

    # ... (기타 browse 및 run 함수들 생략 - 제공해주신 코드와 동일) ...
    def browse_image_input(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Select Input Image', '', 'Images (*.png *.jpg *.jpeg *.bmp)')
        if file_path: self.img_input_edit.setText(file_path)

    def browse_video_input(self):
        file_path, _ = QFileDialog.getOpenFileName(self, 'Select Input Video', '', 'Videos (*.mp4 *.mov *.avi *.mkv)')
        if file_path: self.vid_input_edit.setText(file_path)

    def browse_output_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, 'Select Output Folder')
        if folder_path:
            self.img_output_edit.setText(folder_path)
            self.vid_output_edit.setText(folder_path)

    def run_image_upscale(self):
        input_path = self.img_input_edit.text().strip()
        output_folder = self.img_output_edit.text().strip()
        scale = int(self.img_scale_combo.currentText().replace('x', ''))
        if not os.path.exists(input_path): return
        if not output_folder: output_folder = os.path.dirname(input_path) or '.'
        self.image_worker = ImageUpscaleWorker(input_path, output_folder, scale)
        self.image_worker.progress.connect(self.img_progress.setValue)
        self.image_worker.finished.connect(self.on_image_finished)
        self.image_worker.start()

    def run_video_upscale(self):
        input_path = self.vid_input_edit.text().strip()
        output_folder = self.vid_output_edit.text().strip()
        num_splits = self.split_spin.value()
        tile = self.tile_spin.value()
        scale = int(self.vid_scale_combo.currentText().replace('x', ''))
        if not os.path.exists(input_path) or not output_folder: return
        target_text = self.target_parts_edit.text().strip()
        try:
            target_parts = [int(x) for x in re.split(r'\s*,\s*', target_text) if x != '']
        except: return
        self.video_worker = VideoUpscaleWorker(input_path, output_folder, num_splits, target_parts, tile, scale)
        self.video_worker.progress.connect(self.vid_progress.setValue)
        self.video_worker.log.connect(self.append_video_log)
        self.video_worker.finished.connect(self.on_video_finished)
        self.video_worker.start()

    def append_image_log(self, message): self.img_log.append(message)
    def append_video_log(self, message): self.vid_log.append(message)
    def on_image_finished(self, message): self.img_progress.setValue(100)
    def on_video_finished(self, message): self.vid_progress.setValue(100)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = UpscaleApp()
    window.show()
    sys.exit(app.exec_())