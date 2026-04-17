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

    def initUI(self):
        from UpscaleImg import create_image_tab
        from UpscaleVid import create_video_tab
        self.resize(1050, 850)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.base_layout = QVBoxLayout(self.central_widget)
        self.tabs = QTabWidget()
        self.image_tab = create_image_tab(self, self.translations)
        self.video_tab = create_video_tab(self, self.translations)
        self.video_merge_tab = VideoMergeTab(self)
        self.tabs.addTab(self.image_tab, "")
        self.tabs.addTab(self.video_tab, "")
        self.tabs.addTab(self.video_merge_tab, "")
        self.base_layout.addWidget(self.tabs)
        self.info_panel = QHBoxLayout()
        self.sys_info_label = QLabel(get_detailed_system_info())
        self.info_panel.addWidget(self.sys_info_label)
        self.base_layout.addLayout(self.info_panel)
        self.update_language()
        apply_app_theme(self, self.theme)
        self.show()

    def t(self, key): return UI_TEXTS[self.language].get(key, key)

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

    def update_language(self):
        lang = self.language
        self.setWindowTitle(UI_TEXTS[lang]['window_title'])
        self.tabs.setTabText(0, UI_TEXTS[lang]['tab_image'])
        self.tabs.setTabText(1, UI_TEXTS[lang]['tab_video'])
        self.tabs.setTabText(2, UI_TEXTS[lang]['tab_video_merge'])
        self.img_run_btn.setText(UI_TEXTS[lang]['upscale_image'])
        self.vid_run_btn.setText(UI_TEXTS[lang]['run_video_upscale'])

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
        num_splits = self.split_spin.value()
        model_path = self.vid_model_combo.currentData()
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
                    target_parts, self.tile_spin.value(), model_path
                )
                self.vid_worker.progress.connect(self.vid_progress.setValue)
                self.vid_worker.log.connect(self.vid_log.append)
                self.vid_worker.finished.connect(self.on_video_finished)
                self.vid_worker.start()
            else:
                self.vid_run_btn.setEnabled(True)
        self.ensure_ffmpeg(log_func=self.vid_log.append, progress_func=self.vid_progress.setValue, finished_callback=on_ffmpeg_ready)

    def on_video_finished(self, msg):
        self.vid_log.append(msg)
        self.vid_run_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UpscaleApp()
    sys.exit(app.exec_())