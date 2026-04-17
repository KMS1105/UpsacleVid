import sys
import os
import time
import platform
import logging
import subprocess
import shutil
import zipfile
import urllib.request
import threading
from PyQt5.QtWidgets import (
    QMainWindow, QApplication, QTabWidget, QWidget, QVBoxLayout, 
    QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem,
    QAbstractItemView, QFileDialog, QMessageBox, QListView, QLineEdit,
    QProgressBar, QTextEdit, QComboBox, QSpinBox, QFrame, QMenuBar, QMenu,
    QSizePolicy, QDesktopWidget
)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QRect
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor

from setting import (
    UI_TEXTS, apply_app_theme, get_device_info_text, 
    get_device_recommendation, get_detailed_system_info,
    get_torch_install_command, get_hardware_gpu_name,
    prepare_model, prepare_ffmpeg
)
from VideoMerge import VideoMergeTab

ffmpeg_path = shutil.which('ffmpeg')
print(f"DEBUG: 현재 시스템이 인식하는 FFmpeg 경로: {ffmpeg_path}")

class UpscaleApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = 'ko'
        self.theme = 'light'
        self.translations = []
        self.verify_torch_environment()
        self.initUI()
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(500, self.check_ffmpeg_on_launch)

    def check_ffmpeg_on_launch(self):
        def on_init_ffmpeg_ready(success):
            self.vid_progress.setValue(0)
            if success:
                self.vid_log.append(f"[{time.strftime('%H:%M:%S')}] ✅ FFmpeg 준비 완료")
            else:
                self.vid_log.append(f"[{time.strftime('%H:%M:%S')}] ❌ FFmpeg 초기 준비 실패")
        self.ensure_ffmpeg(log_func=self.vid_log.append, progress_func=self.vid_progress.setValue, finished_callback=on_init_ffmpeg_ready)

    def ensure_ffmpeg(self, log_func=None, progress_func=None, finished_callback=None):
        def download_task():
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            success = prepare_ffmpeg(base_dir, log_func, progress_func)
            if finished_callback: finished_callback(success)
        threading.Thread(target=download_task, daemon=True).start()
    
    def verify_torch_environment(self):
        need_fix = False
        try:
            import torch
            if not torch.cuda.is_available() and get_hardware_gpu_name(): need_fix = True
        except:
            need_fix = True
        if need_fix:
            cmd = get_torch_install_command()
            if cmd and QMessageBox.question(self, "CUDA 가속 설정", "NVIDIA GPU 가속을 위해 전용 라이브러리 설치가 필요합니다.\n재설치할까요?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "-y"])
                    subprocess.check_call([sys.executable, "-m", "pip"] + cmd.split())
                    sys.exit()
                except Exception as e:
                    QMessageBox.critical(self, "실패", f"설치 중 오류: {e}")

    def t(self, key):
        return UI_TEXTS[self.language].get(key, key)
    
    def initUI(self):
        self.setWindowIcon(QIcon('icon.png'))
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.create_menu()

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        from UpscaleImg import create_image_tab
        self.image_tab = create_image_tab(self, [])
        self.tabs.addTab(self.image_tab, "")

        from UpscaleVid import create_video_tab
        self.video_tab = create_video_tab(self, [])
        self.tabs.addTab(self.video_tab, "")

        self.video_merge_tab = VideoMergeTab(self)
        self.tabs.addTab(self.video_merge_tab, "")

        info_layout = QHBoxLayout()
        self.device_info_label = QLabel()
        info_layout.addWidget(self.device_info_label)
        main_layout.addLayout(info_layout)

        self.update_language()
        self.apply_theme(self.theme)
        self.resize(1000, 800)
        self.show()
    
    def create_menu(self):
        menubar = self.menuBar()
        
        self.theme_menu = menubar.addMenu("")
        self.light_action = self.theme_menu.addAction("", lambda: self.apply_theme('light'))
        self.dark_action = self.theme_menu.addAction("", lambda: self.apply_theme('dark'))

        self.lang_menu = menubar.addMenu("")
        self.ko_action = self.lang_menu.addAction("", lambda: self.change_language('ko'))
        self.en_action = self.lang_menu.addAction("", lambda: self.change_language('en'))
        
    def apply_theme(self, theme="light"):
        if theme: 
            self.theme = theme

        from setting import apply_app_theme
        apply_app_theme(QApplication.instance(), self.theme)

    def change_theme(self, theme):
        self.theme = theme
        apply_app_theme(self, self.theme)

    def change_language(self, lang):
        self.language = lang
        self.update_language()

    def browse_image_input(self):
        file, _ = QFileDialog.getOpenFileName(self, self.t('input_image'), '', 'Images (*.png *.jpg *.jpeg *.webp *.bmp)')
        if file: self.img_input_edit.setText(file)

    def browse_video_input(self):
        file, _ = QFileDialog.getOpenFileName(self, self.t('input_video'), '', 'Videos (*.mp4 *.avi *.mkv *.mov)')
        if file: self.vid_input_edit.setText(file)

    def browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t('output_folder'))
        if folder:
            if self.tabs.currentIndex() == 0: self.img_output_edit.setText(folder)
            else: self.vid_output_edit.setText(folder)
            
    def setup_menus(self):
        menubar = self.menuBar()
        
        theme_menu = menubar.addMenu(self.t('menu_theme'))
        light_action = theme_menu.addAction(self.t('menu_light'))
        light_action.triggered.connect(lambda: self.change_theme('light'))
        dark_action = theme_menu.addAction(self.t('menu_dark'))
        dark_action.triggered.connect(lambda: self.change_theme('dark'))

        lang_menu = menubar.addMenu(self.t('menu_language'))
        ko_action = lang_menu.addAction(self.t('lang_ko'))
        ko_action.triggered.connect(lambda: self.change_language('ko'))
        en_action = lang_menu.addAction(self.t('lang_en'))
        en_action.triggered.connect(lambda: self.change_language('en'))

    def update_language(self):
        self.setWindowTitle(self.t('window_title'))
        self.tabs.setTabText(0, self.t('tab_image'))
        self.tabs.setTabText(1, self.t('tab_video'))
        self.tabs.setTabText(2, self.t('tab_video_merge'))

        if hasattr(self, 'device_info_label'):
            header = self.t('device_label')
            system_spec = get_detailed_system_info() 
            self.device_info_label.setText(f"{header} {system_spec}")

        if hasattr(self, 'img_input_label'):
            self.img_input_label.setText(self.t('input_image'))
            self.img_input_label.parent().findChild(QPushButton).setToolTip(self.t('input_image_tip'))
            self.img_output_label.setText(self.t('output_folder'))
            self.img_output_label.parent().findChild(QPushButton).setToolTip(self.t('output_folder_tip'))
            self.img_model_label.setText(self.t('model_select'))
            self.img_model_label.parent().findChild(QPushButton).setToolTip(self.t('model_select_tip'))
            self.img_tile_label.setText(self.t('tile_size'))
            self.img_tile_label.parent().findChild(QPushButton).setToolTip(self.t('tile_size_tip'))
            self.img_run_btn.setText(self.t('upscale_image'))
            self.img_recommend_label.setText(get_device_recommendation(self.language))

        if hasattr(self, 'vid_input_label'):
            self.vid_input_label.setText(self.t('input_video'))
            self.vid_input_label.parent().findChild(QPushButton).setToolTip(self.t('input_video_tip'))
            self.vid_output_label.setText(self.t('output_folder'))
            self.vid_output_label.parent().findChild(QPushButton).setToolTip(self.t('output_folder_tip'))
            self.vid_split_label.setText(self.t('split_count'))
            self.vid_split_label.parent().findChild(QPushButton).setToolTip(self.t('split_count_tip'))
            self.vid_tile_label.setText(self.t('tile_size'))
            self.vid_tile_label.parent().findChild(QPushButton).setToolTip(self.t('tile_size_tip'))
            self.vid_target_label.setText(self.t('target_parts'))
            self.vid_target_label.parent().findChild(QPushButton).setToolTip(self.t('target_parts_tip'))
            self.vid_run_btn.setText(self.t('run_video_upscale'))
            self.vid_recommend_label.setText(get_device_recommendation(self.language))
            
            if hasattr(self, 'vid_model_label'):
                self.vid_model_label.setText(self.t('model_select'))
                self.vid_model_label.parent().findChild(QPushButton).setToolTip(self.t('model_select_tip'))

        if hasattr(self, 'video_merge_tab'):
            vmt = self.video_merge_tab
            vmt.lbl_input.setText(self.t('input_folder'))
            vmt.lbl_audio.setText(self.t('audio_file'))
            vmt.btn_browse_input.setText(self.t('select_folder'))
            vmt.btn_browse_audio.setText(self.t('select_audio'))
            vmt.btn_clear_audio.setText(self.t('clear_audio'))
            vmt.lbl_worklist.setText(self.t('work_list'))
            vmt.btn_run.setText(self.t('run_auto_merge'))

        self.theme_menu.setTitle(self.t('menu_theme'))
        self.lang_menu.setTitle(self.t('menu_language'))
        self.light_action.setText(self.t('menu_light'))
        self.dark_action.setText(self.t('menu_dark'))
        self.ko_action.setText(self.t('lang_ko'))
        self.en_action.setText(self.t('lang_en'))

    def run_image_upscale(self):
        from UpscaleImg import ImageUpscaleWorker
        input_path = self.img_input_edit.text()
        output_folder = self.img_output_edit.text()
        model_path = self.img_model_combo.currentData()
        tile_size = self.img_tile_spin.value()
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Error", "입력 파일을 선택해주세요.")
            return
        self.img_run_btn.setEnabled(False)
        self.img_worker = ImageUpscaleWorker(input_path, output_folder, model_path, tile_size)
        self.img_worker.progress.connect(self.img_progress.setValue)
        self.img_worker.log.connect(self.img_log.append)
        self.img_worker.finished.connect(self.on_image_finished)
        self.img_worker.start()
        
    def on_image_finished(self, msg):
        self.img_log.append(msg)
        self.img_run_btn.setEnabled(True)

    def run_video_upscale(self):
        self.vid_run_btn.setEnabled(False)
        input_path = self.vid_input_edit.text()
        output_folder = self.vid_output_edit.text()
        num_splits = self.vid_split_spin.value()
        model_path = self.vid_model_combo.currentData()
        tile_size = self.vid_tile_spin.value()
        target_text = self.target_parts_edit.text()
    
        try:
            target_parts = []
            for part in target_text.replace(" ", "").split(','):
                if '~' in part:
                    start, end = map(int, part.split('~'))
                    target_parts.extend(range(start, end + 1))
                else:
                    target_parts.append(int(part))
        except ValueError:
            QMessageBox.warning(self, "입력 오류", "대상 파트 형식이 올바르지 않습니다. (예: 0~9)")
            self.vid_run_btn.setEnabled(True)
            return
        
        def on_ffmpeg_ready(success):
            from UpscaleVid import VideoUpscaleWorker
            if success:
                self.vid_worker = VideoUpscaleWorker(
                    input_path, output_folder, num_splits, 
                    target_parts, tile_size, model_path
                )
                self.vid_worker.progress.connect(self.vid_progress.setValue)
                self.vid_worker.log.connect(self.vid_log.append)
                self.vid_worker.finished.connect(self.on_video_finished)
                self.vid_worker.start()
            else:
                self.vid_run_btn.setEnabled(True)
                self.vid_log.append("FFmpeg 준비 실패")

        self.ensure_ffmpeg(
            log_func=self.vid_log.append, 
            progress_func=self.vid_progress.setValue, 
            finished_callback=on_ffmpeg_ready
        )
        
    def on_video_finished(self, msg):
        self.vid_log.append(msg)
        self.vid_run_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UpscaleApp()
    sys.exit(app.exec_())