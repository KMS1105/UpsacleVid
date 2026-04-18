import os
import subprocess
import platform
import shutil
import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QMessageBox, QApplication, QTextEdit, QLineEdit, QProgressBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from setting import UI_TEXTS

def find_ffmpeg_bin(search_root):
    for root, dirs, files in os.walk(search_root):
        if "ffmpeg.exe" in files:
            full_path = os.path.join(root, "ffmpeg.exe")
            if "bin" in root.lower():
                return full_path
    return None

class MergeWorker(QThread):
    finished = pyqtSignal(bool, str)
    log = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, video_paths, output_path, audio_path=None):
        super().__init__()
        self.video_paths = video_paths
        self.output_path = output_path
        self.audio_path = audio_path
        self.total_duration = 0

    def get_duration(self, ffmpeg_exe, file_path):
        try:
            cmd = [ffmpeg_exe, '-i', file_path]
            result = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0)
            match = re.search(r"Duration:\s(\d+):(\d+):(\d+\.\d+)", result.stderr)
            if match:
                h, m, s = map(float, match.groups())
                return h * 3600 + m * 60 + s
        except: pass
        return 0

    def run(self):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.dirname(current_dir)
            ffmpeg_search_root = os.path.join(base_dir, "ffmpeg")
            ffmpeg_exe = find_ffmpeg_bin(ffmpeg_search_root) or shutil.which("ffmpeg") or 'ffmpeg'

            self.total_duration = sum(self.get_duration(ffmpeg_exe, p) for p in self.video_paths)

            list_path = os.path.join(os.path.dirname(self.output_path), "merge_list.txt")
            with open(list_path, 'w', encoding='utf-8') as f:
                for path in self.video_paths:
                    abs_path = os.path.abspath(path).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")

            cmd = [ffmpeg_exe, '-y', '-f', 'concat', '-safe', '0', '-i', list_path]
            if self.audio_path:
                cmd.extend(['-i', self.audio_path, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-shortest'])
            else:
                cmd.extend(['-c', 'copy'])
            cmd.append(self.output_path)
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                     universal_newlines=True, encoding='utf-8', 
                                     creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0)
            
            filter_keywords = ['frame=', 'size=', 'time=', 'bitrate=', 'speed=', 'Qavg', '[aac', 'Press [q]']

            for line in process.stdout:
                clean_line = line.strip()
                if not clean_line: continue
                
                time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", clean_line)
                if time_match and self.total_duration > 0:
                    h, m, s = map(float, time_match.groups())
                    current_time = h * 3600 + m * 60 + s
                    p = int((current_time / self.total_duration) * 100)
                    self.progress.emit(min(p, 100))

                if any(kw in clean_line for kw in filter_keywords): continue
                self.log.emit(clean_line)
            
            process.wait()
            if os.path.exists(list_path): os.remove(list_path)
            self.progress.emit(100 if process.returncode == 0 else 0)
            self.finished.emit(process.returncode == 0, self.output_path if process.returncode == 0 else "Merge failed")
        except Exception as e:
            self.finished.emit(False, str(e))

class VideoMergeTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.input_video_paths = []
        self.selected_audio_path = None
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)

        input_layout = QHBoxLayout()
        self.lbl_input = QLabel(self.parent.t('input_folder'))
        input_layout.addWidget(self.lbl_input)
        self.input_path_edit = QLineEdit()
        input_layout.addWidget(self.input_path_edit)
        self.btn_browse_input = QPushButton(self.parent.t('select_folder'))
        self.btn_browse_input.clicked.connect(self.select_input_folder)
        input_layout.addWidget(self.btn_browse_input)
        layout.addLayout(input_layout)

        audio_layout = QHBoxLayout()
        self.lbl_audio = QLabel(self.parent.t('audio_file'))
        audio_layout.addWidget(self.lbl_audio)
        self.audio_path_edit = QLineEdit(); self.audio_path_edit.setReadOnly(True)
        audio_layout.addWidget(self.audio_path_edit)
        self.btn_browse_audio = QPushButton(self.parent.t('select_audio'))
        self.btn_browse_audio.clicked.connect(self.select_audio_file)
        audio_layout.addWidget(self.btn_browse_audio)
        self.btn_clear_audio = QPushButton(self.parent.t('clear_audio'))
        self.btn_clear_audio.clicked.connect(self.clear_audio_selection)
        audio_layout.addWidget(self.btn_clear_audio)
        layout.addLayout(audio_layout)

        self.lbl_worklist = QLabel(self.parent.t('work_list'))
        layout.addWidget(self.lbl_worklist)
        self.merge_log = QTextEdit(); self.merge_log.setReadOnly(True)
        layout.addWidget(self.merge_log)

        self.merge_progress = QProgressBar()
        layout.addWidget(self.merge_progress)

        self.btn_run = QPushButton(self.parent.t('run_merge'))
        self.btn_run.setFixedHeight(40); self.btn_run.clicked.connect(self.run_merge)
        layout.addWidget(self.btn_run)

    def natural_sort_key(self, s):
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

    def select_input_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, 'Select Folder')
        if dir_path:
            self.input_path_edit.setText(dir_path)
            files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) if f.lower().endswith(('.mp4', '.ts', '.mkv', '.mov'))]
            files.sort(key=self.natural_sort_key)
            if files:
                self.input_video_paths = files
                self.merge_log.clear()
                self.merge_progress.setValue(0)
                self.merge_log.append(self.parent.t('log_files_found').format(len(files)))
                
                for f in files:
                    file_name = os.path.basename(f)
                    self.merge_log.append(self.parent.t('log_file_item').format(file_name))
            else:
                QMessageBox.warning(
                    self, 
                    self.parent.t('warn_no_video_title'), 
                    self.parent.t('warn_no_video_msg')
                )

    def select_audio_file(self):
        file, _ = QFileDialog.getOpenFileName(
            self,                                  
            self.parent.t('audio_select_title'),  
            '',                                    
            self.parent.t('audio_select_filter')   
        )
        if file:
            self.selected_audio_path = file
            self.audio_path_edit.setText(os.path.basename(file))
            self.merge_log.append(self.parent.t('log_audio_source').format(os.path.basename(file)))
            
    def clear_audio_selection(self):
        self.selected_audio_path = None
        self.audio_path_edit.clear()
        self.merge_log.append(self.parent.t('log_audio_none'))

    def run_merge(self):
        if not self.input_video_paths:
            QMessageBox.warning(
                self, 
                self.parent.t('warn_no_folder_title'), 
                self.parent.t('warn_no_folder_msg')
            )
            return

        save_path, _ = QFileDialog.getSaveFileName(
                self, 
                self.parent.t('save_dialog_title'), 
                'final_merged.mp4', 
                self.parent.t('save_dialog_filter')
            )
        if save_path:
            self.btn_run.setEnabled(False)
            self.merge_progress.setValue(0)
            self.worker = MergeWorker(self.input_video_paths, save_path, self.selected_audio_path)
            self.worker.log.connect(self.merge_log.append)
            self.worker.progress.connect(self.merge_progress.setValue)
            self.worker.finished.connect(self.on_merge_finished)
            self.worker.start()

    def on_merge_finished(self, success, msg):
        self.btn_run.setEnabled(True)
        if success:
            self.merge_log.append(self.parent.t('log_merge_success').format(msg))
            QMessageBox.information(
                self, 
                self.parent.t('msg_merge_success_title'), 
                self.parent.t('msg_merge_success_text')
            )
        else:
            self.merge_log.append(self.parent.t('log_merge_fail').format(msg))
            QMessageBox.critical(
                self, 
                self.parent.t('msg_merge_fail_title'), 
                self.parent.t('msg_merge_fail_text').format(msg)
            )