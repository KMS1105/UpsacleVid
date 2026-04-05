import os
import re
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QTabWidget, QVBoxLayout, QMenuBar, QFileDialog, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

from setting import UI_TEXTS, get_device_info_text, get_device_recommendation, apply_app_theme
from UpscaleImg import create_image_tab, ImageUpscaleWorker
from UpscaleVid import create_video_tab, VideoUpscaleWorker

def create_label_with_info(parent, text_key, tooltip_key):
    container = QWidget()
    hl = QHBoxLayout(container)
    hl.setContentsMargins(0, 0, 0, 0)
    label = QLabel(parent.t(text_key))
    info = QPushButton('!')
    info.setToolTip(parent.t(tooltip_key))
    info.setProperty("class", "help-button")
    info.setFixedSize(20, 20)
    info.setCursor(Qt.PointingHandCursor)
    hl.addWidget(label)
    hl.addWidget(info)
    if hasattr(parent, 'translations'):
        parent.translations.append((label, 'setText', text_key))
        parent.translations.append((info, 'setToolTip', tooltip_key))
    return container

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
        self.setGeometry(120, 120, 760, 620)
        self.menu_bar = QMenuBar()
        main_layout = QVBoxLayout()
        main_layout.setMenuBar(self.menu_bar)
        self.tabs = QTabWidget()
        self.tabs.addTab(create_image_tab(self, self.translations), self.t('tab_image'))
        self.tabs.addTab(create_video_tab(self, self.translations), self.t('tab_video'))
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
        for widget, method, key in self.translations:
            getattr(widget, method)(self.t(key))
        self.img_device_label.setText(get_device_info_text(self.language))
        self.vid_device_label.setText(get_device_info_text(self.language))
        self.img_recommend_label.setText(get_device_recommendation(self.language))
        self.vid_recommend_label.setText(get_device_recommendation(self.language))
        self.img_run_btn.setText(self.t('upscale_image'))
        self.vid_run_btn.setText(self.t('run_video_upscale'))
        self.img_browse_btn.setText(self.t('browse'))
        self.img_output_browse_btn.setText(self.t('browse'))
        self.vid_browse_btn.setText(self.t('browse'))
        self.output_browse_btn.setText(self.t('browse'))

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
        if not os.path.exists(input_path):
            self.append_image_log(self.t('error_input_missing').format(input_path))
            return
        if not output_folder: output_folder = os.path.dirname(input_path) or '.'
        self.append_image_log(self.t('start_image'))
        self.img_progress.setValue(5)
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
        if not os.path.exists(input_path):
            self.append_video_log(self.t('error_input_missing').format(input_path))
            return
        if not output_folder:
            self.append_video_log(self.t('error_no_output'))
            return
        target_text = self.target_parts_edit.text().strip()
        try:
            target_parts = [int(x) for x in re.split(r'\s*,\s*', target_text) if x != '']
        except ValueError:
            self.append_video_log(self.t('error_target_parts'))
            return
        if not target_parts:
            self.append_video_log(self.t('error_no_target_parts'))
            return
        self.append_video_log(self.t('start_video'))
        self.vid_progress.setValue(5)
        self.video_worker = VideoUpscaleWorker(input_path, output_folder, num_splits, target_parts, tile, scale)
        self.video_worker.progress.connect(self.vid_progress.setValue)
        self.video_worker.log.connect(self.append_video_log)
        self.video_worker.finished.connect(self.on_video_finished)
        self.video_worker.start()

    def append_image_log(self, message): self.img_log.append(message)
    def append_video_log(self, message): self.vid_log.append(message)
    def on_image_finished(self, message):
        self.append_image_log(message)
        self.img_progress.setValue(100)
    def on_video_finished(self, message):
        self.append_video_log(message+"\n")
        self.vid_progress.setValue(100)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = UpscaleApp()
    window.show()
    sys.exit(app.exec_())