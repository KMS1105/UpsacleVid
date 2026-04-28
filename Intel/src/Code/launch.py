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
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QRect, QMetaObject, Q_ARG
from PyQt5.QtGui import QIcon, QFont, QPixmap, QColor

from setting import (
    UI_TEXTS, apply_app_theme, get_device_info_text, 
    get_device_recommendation, get_detailed_system_info,
    get_torch_install_command, get_hardware_gpu_name,
    prepare_model, prepare_ffmpeg
)
from VideoMerge import VideoMergeTab
from RemoveBG import RemoveBGTab

class UpscaleApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.language = 'en'
        self.theme = 'light'
        self.translations = []
        self.verify_torch_environment()
        self.initUI()
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(500, self.check_ffmpeg_on_launch)

    def check_ffmpeg_on_launch(self):
        def on_init_ffmpeg_ready(success):
            self.vid_progress.setValue(0)
            timestamp = time.strftime('%H:%M:%S')
            if success:
                self.vid_log.append(f"[{timestamp}] {self.t('log_ffmpeg_ready')}")
            else:
                self.vid_log.append(f"[{timestamp}] {self.t('log_ffmpeg_fail')}")
        self.ensure_ffmpeg(log_func=self.vid_log.append, progress_func=self.vid_progress.setValue, finished_callback=on_init_ffmpeg_ready)
        
    def ensure_ffmpeg(self, log_func=None, progress_func=None, finished_callback=None):
        def download_task():
            if getattr(sys, 'frozen', False):
                base_dir = os.path.join(os.path.dirname(sys.executable), "src")
            else:
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
        
        self.tab_remove_bg = RemoveBGTab(self)
        self.tabs.addTab(self.tab_remove_bg, self.t('remove_bg_tab_name'))

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
        self.refresh_ui_texts()

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
        self.tabs.setTabText(3, self.t('tab_remove_bg'))
        
        if hasattr(self, 'img_run_btn'):
            self.img_run_btn.setText(self.t('upscale_image'))
        if hasattr(self, 'img_recommend_label'):
            self.img_recommend_label.setText(get_device_recommendation(self.language))
        if hasattr(self, 'vid_run_btn'):
            self.vid_run_btn.setText(self.t('run_video_upscale'))
        if hasattr(self, 'vid_recommend_label'):
            self.vid_recommend_label.setText(get_device_recommendation(self.language))
        if hasattr(self, 'video_merge_tab'):
            self.video_merge_tab.btn_run.setText(self.t('run_merge'))
            
        if hasattr(self, 'tab_remove_bg'):
            self.tab_remove_bg.update_ui_texts()

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
            
            if hasattr(self, 'vid_model_label'):
                self.vid_model_label.setText(self.t('model_select'))
                btn = self.vid_model_label.parent().findChild(QPushButton)
                if btn: btn.setToolTip(self.t('model_select_tip'))
                
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
            vmt.btn_run.setText(self.t('run_merge'))

        self.theme_menu.setTitle(self.t('menu_theme'))
        self.lang_menu.setTitle(self.t('menu_language'))
        self.light_action.setText(self.t('menu_light'))
        self.dark_action.setText(self.t('menu_dark'))
        self.ko_action.setText(self.t('lang_ko'))
        self.en_action.setText(self.t('lang_en'))
        
        timestamp = time.strftime('%H:%M:%S')
        current_lang_display = self.t('lang_name')
        log_msg = f"[{timestamp}] {self.t('log_lang_changed').format(current_lang_display)}"
        
        if hasattr(self, 'img_log'): 
            self.img_log.append(log_msg)
        if hasattr(self, 'vid_log'): 
            self.vid_log.append(log_msg)
        if hasattr(self, 'video_merge_tab'):
            self.video_merge_tab.merge_log.append(log_msg)

    def run_image_upscale(self):
        from UpscaleImg import ImageUpscaleWorker
        input_path = self.img_input_edit.text()
        output_folder = self.img_output_edit.text()
        model_path = self.img_model_combo.currentData()
        tile_size = self.img_tile_spin.value()
        lang = getattr(self, 'lang', 'ko')
        QMessageBox.warning(
            self, 
            UI_TEXTS[lang]['err_input_title'], 
            UI_TEXTS[lang]['err_input_msg']
        )
        self.img_run_btn.setEnabled(False)
        self.img_worker = ImageUpscaleWorker(input_path, output_folder, model_path, tile_size)
        self.img_worker.progress.connect(self.img_progress.setValue)
        self.img_worker.log.connect(self.img_log.append)
        self.tab_bg.worker.log.connect(self.tab_bg.log.append)
        self.img_worker.finished.connect(self.on_image_finished)
        self.img_worker.start()
        
    def on_image_finished(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        if '|' in msg:
            key, data = msg.split('|', 1)
            translated_msg = self.t(key).format(data) if key in UI_TEXTS.get(self.language, {}) else msg
        else:
            translated_msg = self.t(msg) if msg in UI_TEXTS.get(self.language, {}) else msg
        self.img_log.append(f"[{timestamp}] {translated_msg}")
        self.img_run_btn.setEnabled(True)
        
    def refresh_ui_texts(self):
        for btn in self.findChildren(QPushButton):
            if hasattr(btn, 'text_key'):
                btn.setText(self.t(btn.text_key))
        
    def handle_video_log(self, raw_msg):
        if hasattr(self, 'last_log') and self.last_log == raw_msg:
            return
        self.last_log = raw_msg
        
        timestamp = time.strftime('%H:%M:%S')
        translated = raw_msg 

        if '|' in raw_msg:
            parts = raw_msg.split('|', 1)
            key, data_str = parts[0], parts[1]
            if key in UI_TEXTS.get(self.language, {}):
                try:
                    if key == 'log_device_info':
                        from setting import get_hardware_gpu_name
                        translated = self.t(key).format(get_hardware_gpu_name())
                    elif key == 'log_model_info':
                        model_name = os.path.basename(data_str).replace('.pth', '').replace('.xml', '')
                        translated = self.t(key).format(model_name)
                    elif key == 'log_res_optimized':
                        translated = self.t(key).format(*data_str.split('x'))
                    else:
                        translated = self.t(key).format(*data_str.split('|'))
                except Exception:
                    translated = self.t(key)
        elif raw_msg in UI_TEXTS.get(self.language, {}):
            translated = self.t(raw_msg)
        
        final_text = f"[{timestamp}] {translated}"
        if self.vid_log.document().blockCount() > 500:
            self.vid_log.clear()
            self.vid_log.append("[System] Log cleared to prevent memory overflow.")

        QMetaObject.invokeMethod(
            self.vid_log, 
            "append", 
            Qt.QueuedConnection, 
            Q_ARG(str, final_text)
        )

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
            lang = getattr(self, 'lang', 'ko')
            QMessageBox.warning(
                self, 
                UI_TEXTS[lang]['err_part_title'], 
                UI_TEXTS[lang]['err_part_msg']
            )
            self.vid_run_btn.setEnabled(True)
            return
        
        def on_ffmpeg_ready(success):
            from UpscaleVid import VideoUpscaleWorker
            if success:
                self.vid_worker = VideoUpscaleWorker(
                    input_path=input_path, 
                    output_folder=output_folder, 
                    num_splits=num_splits, 
                    target_parts=target_parts, 
                    tile=tile_size, 
                    model_path=model_path
                )
                self.vid_worker.progress.connect(self.vid_progress.setValue)
                self.vid_worker.log.connect(self.handle_video_log)
                self.vid_worker.finished.connect(self.on_video_finished)
                self.vid_worker.start()
            else:
                self.vid_run_btn.setEnabled(True)
                self.vid_log.append(self.t('log_ffmpeg_fail')) 

        self.ensure_ffmpeg(
            log_func=self.vid_log.append, 
            progress_func=self.vid_progress.setValue, 
            finished_callback=on_ffmpeg_ready
        )
        
    def on_video_finished(self):
        self.vid_run_btn.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UpscaleApp()
    sys.exit(app.exec_())