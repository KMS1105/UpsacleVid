#Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

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
    prepare_model
)

from VideoMerge import VideoMergeTab

def ensure_ffmpeg(log_func=None, progress_func=None, finished_callback=None):
    def download_task():
        if shutil.which("ffmpeg"):
            if finished_callback: finished_callback(True)
            return

        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(current_file_dir)
        ffmpeg_dir = os.path.join(src_dir, "ffmpeg")
        
        actual_bin_path = ""
        if os.path.exists(ffmpeg_dir):
            for root, dirs, files in os.walk(ffmpeg_dir):
                if "ffmpeg.exe" in files:
                    actual_bin_path = root
                    break

        if actual_bin_path:
            if actual_bin_path not in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + actual_bin_path
            if finished_callback: finished_callback(True)
            return

        if log_func: log_func("⚠️ FFmpeg를 찾을 수 없습니다. src/ffmpeg에 설치를 시작합니다...")
        
        try:
            os.makedirs(ffmpeg_dir, exist_ok=True)
            zip_path = os.path.join(ffmpeg_dir, "ffmpeg.zip")
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            
            def report_progress(block_num, block_size, total_size):
                if total_size > 0 and progress_func:
                    percent = int(block_num * block_size * 100 / total_size)
                    progress_func(min(percent, 100))

            urllib.request.urlretrieve(url, zip_path, reporthook=report_progress)
            
            if log_func: log_func("📦 압축 해제 중...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(ffmpeg_dir)
            
            new_bin_path = ""
            for root, dirs, files in os.walk(ffmpeg_dir):
                if "ffmpeg.exe" in files:
                    new_bin_path = root
                    break
            
            if new_bin_path:
                if new_bin_path not in os.environ["PATH"]:
                    os.environ["PATH"] += os.pathsep + new_bin_path
                if log_func: log_func(f"✅ FFmpeg 설치 완료: {new_bin_path}")
            
            if os.path.exists(zip_path):
                os.remove(zip_path)
                
            if finished_callback: finished_callback(True)
        except Exception as e:
            if log_func: log_func(f"❌ 설치 중 오류 발생: {e}")
            if finished_callback: finished_callback(False)

    thread = threading.Thread(target=download_task, daemon=True)
    thread.start()

class UpscaleApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = 'ko'
        self.theme = 'light'
        self.translations = []
        self.verify_torch_environment()
        self.initUI()
    
    def verify_torch_environment(self):
        need_fix = False
        try:
            import torch
            if not torch.cuda.is_available():
                if get_hardware_gpu_name(): need_fix = True
        except:
            need_fix = True

        if need_fix:
            cmd = get_torch_install_command()
            if cmd:
                ret = QMessageBox.question(self, "CUDA 가속 설정", 
                    "NVIDIA GPU 가속을 위해 전용 라이브러리 설치가 필요합니다.\n재설치할까요?",
                    QMessageBox.Yes | QMessageBox.No)
                
                if ret == QMessageBox.Yes:
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "torch", "torchvision", "torchaudio", "-y"])
                        subprocess.check_call([sys.executable, "-m", "pip"] + cmd.split())
                        QMessageBox.information(self, "성공", "설치가 완료되었습니다. 프로그램을 재시작하세요.")
                        sys.exit()
                    except Exception as e:
                        QMessageBox.critical(self, "실패", f"설치 중 오류: {e}")

    def initUI(self):
        from UpscaleImg import create_image_tab
        from UpscaleVid import create_video_tab

        self.resize(1050, 850)
        self.setMinimumSize(950, 750)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.base_layout = QVBoxLayout(self.central_widget)
        
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        self.image_tab = create_image_tab(self, self.translations)
        self.video_tab = create_video_tab(self, self.translations)
        self.video_merge_tab = VideoMergeTab(self)
        
        self.tabs.addTab(self.image_tab, "")
        self.tabs.addTab(self.video_tab, "")
        self.tabs.addTab(self.video_merge_tab, "")
        
        self.base_layout.addWidget(self.tabs)
        
        self.info_panel = QHBoxLayout()
        self.sys_info_label = QLabel()
        self.sys_info_label.setStyleSheet("color: #777; font-size: 11px; padding-left: 10px; font-family: 'Consolas';")
        self.info_panel.addWidget(self.sys_info_label)
        self.base_layout.addLayout(self.info_panel)

        self.update_language()
        apply_app_theme(self, self.theme)
        self.sys_info_label.setText(get_detailed_system_info())
        
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        self.change_theme(self.theme)
        
        self.show()

    def t(self, key):
        return UI_TEXTS[self.language].get(key, key)

    def set_menu(self):
        self.menuBar().clear()
        
        theme_menu = self.menuBar().addMenu(self.t('menu_theme'))
        theme_menu.addAction(self.t('menu_light'), lambda: self.change_theme('light'))
        theme_menu.addAction(self.t('menu_dark'), lambda: self.change_theme('dark'))
        
        lang_menu = self.menuBar().addMenu(self.t('menu_language'))
        lang_menu.addAction(self.t('lang_ko'), lambda: self.change_language('ko'))
        lang_menu.addAction(self.t('lang_en'), lambda: self.change_language('en'))

    def change_theme(self, theme):
        self.theme = theme
        apply_app_theme(self, self.theme)
        for widget in self.findChildren(QWidget):
            apply_app_theme(widget, self.theme)
            
        if hasattr(self, 'video_merge_tab'):
            from PyQt5.QtWidgets import QListWidget
            for list_widget in self.video_merge_tab.findChildren(QListWidget):
                apply_app_theme(list_widget, self.theme)

    def change_language(self, lang):
        self.language = lang
        self.update_language()

    def browse_image_input(self):
        file, _ = QFileDialog.getOpenFileName(self, self.t('input_image'), '', 'Images (*.png *.jpg *.jpeg *.webp *.bmp)')
        if file:
            self.img_input_edit.setText(file)

    def browse_video_input(self):
        file, _ = QFileDialog.getOpenFileName(self, self.t('input_video'), '', 'Videos (*.mp4 *.avi *.mkv *.mov)')
        if file:
            self.vid_input_edit.setText(file)

    def browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t('output_folder'))
        if folder:
            if self.tabs.currentIndex() == 0:
                self.img_output_edit.setText(folder)
            else:
                self.vid_output_edit.setText(folder)

    def update_language(self):
        lang = self.language
        self.setWindowTitle(UI_TEXTS[lang]['window_title'])
        self.set_menu()
        
        self.tabs.setTabText(0, UI_TEXTS[lang]['tab_image'])
        self.tabs.setTabText(1, UI_TEXTS[lang]['tab_video'])
        self.tabs.setTabText(2, UI_TEXTS[lang]['tab_video_merge'])
        
        self.img_recommend_label.setText(get_device_recommendation(lang))
        self.vid_recommend_label.setText(get_device_recommendation(lang))
        
        m_tab = self.video_merge_tab
        m_tab.timeline_title.setText("🎬 " + UI_TEXTS[lang]['video_timeline'])
        m_tab.source_label.setText("📂 " + UI_TEXTS[lang]['video_sources'])
        m_tab.btn_add.setText(UI_TEXTS[lang]['add'])
        m_tab.btn_to_timeline.setText(UI_TEXTS[lang]['add_to_timeline'])
        m_tab.btn_remove.setText(UI_TEXTS[lang]['remove'])
        m_tab.btn_clear.setText(UI_TEXTS[lang]['clear'])
        m_tab.btn_run.setText(UI_TEXTS[lang]['export_video'])
        
        self.img_run_btn.setText(UI_TEXTS[lang]['upscale_image'])
        self.vid_run_btn.setText(UI_TEXTS[lang]['run_video_upscale'])
        
        self.img_browse_btn.setText(UI_TEXTS[lang]['browse'])
        self.img_output_browse_btn.setText(UI_TEXTS[lang]['browse'])
        self.vid_browse_btn.setText(UI_TEXTS[lang]['browse'])
        self.output_browse_btn.setText(UI_TEXTS[lang]['browse'])

        self.img_input_edit.setToolTip(UI_TEXTS[lang]['input_image_tip'])
        self.img_output_edit.setToolTip(UI_TEXTS[lang]['output_folder_tip'])
        self.vid_input_edit.setToolTip(UI_TEXTS[lang]['input_video_tip'])
        self.split_spin.setToolTip(UI_TEXTS[lang]['split_count_tip'])
        self.target_parts_edit.setToolTip(UI_TEXTS[lang]['target_parts_tip'])
        self.tile_spin.setToolTip(UI_TEXTS[lang]['tile_size_tip'])
        
        self.sys_info_label.setText(get_detailed_system_info())

    def run_image_upscale(self):
        from UpscaleImg import ImageUpscaleWorker
        input_path = self.img_input_edit.text()
        output_folder = self.img_output_edit.text()
        model_full_path = self.img_model_combo.currentData()
        
        if not input_path or not os.path.exists(input_path):
            QMessageBox.warning(self, "Error", "입력 파일을 선택해주세요.")
            return
        if not model_full_path:
            QMessageBox.warning(self, "Error", "모델 파일을 선택해주세요.")
            return
            
        self.img_run_btn.setEnabled(False)
        self.img_log.append(f"[{time.strftime('%H:%M:%S')}] {self.t('start_image')}")
        
        self.img_worker = ImageUpscaleWorker(input_path, output_folder, model_full_path)
        self.img_worker.progress.connect(self.img_progress.setValue)
        self.img_worker.log.connect(self.img_log.append)
        self.img_worker.finished.connect(self.on_image_finished)
        self.img_worker.start()
        
    def on_image_finished(self, msg):
        self.img_log.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        self.img_run_btn.setEnabled(True)
        self.img_progress.setValue(0)

    def run_video_upscale(self):
        self.vid_run_btn.setEnabled(False)
        self.vid_progress.setValue(0)
        
        input_path = self.vid_input_edit.text()
        output_folder = self.vid_output_edit.text()
        num_splits = self.split_spin.value()
        model_path = self.vid_model_combo.currentData() # 수정: vid_scale_combo 대신 vid_model_combo 사용
        
        if not os.path.exists(input_path):
            QMessageBox.warning(self, "Error", "입력 비디오 파일을 찾을 수 없습니다.")
            self.vid_run_btn.setEnabled(True)
            return
        if not model_path:
            QMessageBox.warning(self, "Error", "모델 파일을 선택해주세요.")
            self.vid_run_btn.setEnabled(True)
            return

        try:
            raw_text = self.target_parts_edit.text()
            target_parts = []
            for item in raw_text.split(','):
                if '~' in item:
                    start, end = map(int, item.split('~'))
                    target_parts.extend(range(start, end + 1))
                else:
                    target_parts.append(int(item.strip()))
            target_parts = list(set(target_parts))
        except Exception:
            QMessageBox.warning(self, "Error", "Invalid target parts. Use format '0~2' or '0,1,2'")
            self.vid_run_btn.setEnabled(True)
            return

        tile = self.tile_spin.value()

        def on_ffmpeg_ready(success):
            from UpscaleVid import VideoUpscaleWorker
            if success:
                self.vid_log.append(f"[{time.strftime('%H:%M:%S')}] {self.t('start_video')}")
                self.vid_worker = VideoUpscaleWorker(input_path, output_folder, num_splits, target_parts, tile, model_path)
                self.vid_worker.progress.connect(self.vid_progress.setValue)
                self.vid_worker.log.connect(self.vid_log.append)
                self.vid_worker.finished.connect(self.on_video_finished)
                self.vid_worker.start()
            else:
                self.vid_log.append("❌ FFmpeg 준비 실패로 작업을 중단합니다.")
                self.vid_run_btn.setEnabled(True)

        ensure_ffmpeg(
            log_func=self.vid_log.append,
            progress_func=self.vid_progress.setValue,
            finished_callback=on_ffmpeg_ready
        )

    def on_video_finished(self, msg):
        self.vid_log.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        self.vid_run_btn.setEnabled(True)
        self.vid_progress.setValue(0)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = UpscaleApp()
    sys.exit(app.exec_())