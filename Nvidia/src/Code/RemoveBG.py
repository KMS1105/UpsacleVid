import os
import cv2
import torch
import numpy as np
import glob
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QProgressBar, QTextEdit, 
                             QFileDialog, QComboBox)
from PyQt5.QtCore import QThread, pyqtSignal
from setting import prepare_bg_model

class DragLineEdit(QLineEdit):
    dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            path = files[0]
            self.setText(path)
            self.dropped.emit(path)

class RemoveBGWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, input_path, output_path, model_path):
        super().__init__(input_path, output_path, model_path)
        self.input_path = input_path
        self.output_path = output_path
        self.model_path = model_path
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def run(self):
        cap = None
        out = None
        try:
            self.log.emit("log_model_loading|")
            
            net = cv2.dnn.readNetFromONNX(self.model_path)
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
            
            self.log.emit("✅ CUDA 환경 로드 성공")
            
            cap = cv2.VideoCapture(self.input_path)
            w, h = int(cap.get(3)), int(cap.get(4))
            fps = cap.get(5)
            total = int(cap.get(7))
            
            output_file = os.path.join(self.output_path, "result.mp4")
            out = cv2.VideoWriter(output_file, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
            
            i = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                
                blob = cv2.dnn.blobFromImage(frame, 1/255.0, (1024, 1024), swapRB=True, crop=False)
                net.setInput(blob)
                mask = net.forward().squeeze()
                
                mask = cv2.resize(mask, (w, h))
                
                mask[:int(h * 0.1), :] = 0
                mask[int(h * 0.9):, :] = 0
                mask = (mask - mask.min()) / (mask.max() - mask.min() + 1e-6)
                if np.mean(mask) < 0.3:
                    mask = 1 - mask
                
                mask = cv2.GaussianBlur(mask, (3, 3), 0)
                mask = np.where(mask > 0.25, 1.0, 0.0)
                
                mask_3ch = cv2.merge([mask, mask, mask])
                result_frame = (frame * mask_3ch + (1 - mask_3ch) * 255).astype('uint8')
                out.write(result_frame)
                
                i += 1
                if i % 10 == 0 or i == total:
                    self.progress.emit(int(i * 100 / total))
                    self.log.emit(f"log_processing_frame|{i}|{total}|{int(i * 100 / total)}")
            
            self.log.emit("log_bg_process_complete|")
        except Exception as e:
            self.log.emit(f"log_convert_fail|{str(e)}")
        finally:
            if cap: cap.release()
            if out: out.release()
            self.finished.emit()

class RemoveBGTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        layout = QVBoxLayout(self)
        
        row0 = QHBoxLayout()
        self.model_combo = QComboBox()
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedWidth(40)
        self.refresh_btn.clicked.connect(self.refresh_models)
        row0.addWidget(QLabel("Model:"))
        row0.addWidget(self.model_combo)
        row0.addWidget(self.refresh_btn)
        layout.addLayout(row0)
        
        row1 = QHBoxLayout()
        self.input_label = QLabel(self.parent.t('input_video'))
        self.input_edit = DragLineEdit(self)
        self.input_edit.dropped.connect(self.update_default_output)
        self.browse_btn = QPushButton(self.parent.t('browse'))
        self.browse_btn.clicked.connect(self.select_input)
        row1.addWidget(self.input_label)
        row1.addWidget(self.input_edit)
        row1.addWidget(self.browse_btn)
        layout.addLayout(row1)
        
        row2 = QHBoxLayout()
        self.output_label = QLabel(self.parent.t('output_folder'))
        self.output_edit = QLineEdit()
        self.browse_out_btn = QPushButton(self.parent.t('browse'))
        self.browse_out_btn.clicked.connect(lambda: self.output_edit.setText(QFileDialog.getExistingDirectory(self, self.parent.t('output_folder'))))
        row2.addWidget(self.output_label)
        row2.addWidget(self.output_edit)
        row2.addWidget(self.browse_out_btn)
        layout.addLayout(row2)
        
        self.prog = QProgressBar()
        layout.addWidget(self.prog)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        
        self.run_btn = QPushButton(self.parent.t('rbg_start_btn'))
        self.run_btn.clicked.connect(self.start_task)
        layout.addWidget(self.run_btn)
        
        self.refresh_models()

    def refresh_models(self):
        self.model_combo.clear()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        weights_dir = os.path.join(base_dir, 'RemBG')
        files = glob.glob(os.path.join(weights_dir, "*.onnx"))
        model_names = sorted(set([os.path.splitext(os.path.basename(f))[0] for f in files]))
        self.model_combo.addItems(model_names)
        msg = "🔄 모델 목록이 갱신되었습니다." if self.parent.language == 'ko' else "🔄 Model list refreshed."
        self.log.append(msg)

    def select_input(self):
        path, _ = QFileDialog.getOpenFileName()
        if path:
            self.input_edit.setText(path)
            self.update_default_output(path)

    def update_default_output(self, file_path):
        self.output_edit.setText(os.path.dirname(file_path))
            
    def update_ui_texts(self):
        self.run_btn.setText(self.parent.t('rbg_start_btn'))
        self.browse_btn.setText(self.parent.t('browse'))
        self.browse_out_btn.setText(self.parent.t('browse'))
        self.input_label.setText(self.parent.t('input_video'))
        self.output_label.setText(self.parent.t('output_folder'))
            
    def start_task(self):
        if not self.output_edit.text(): return
        
        model_path = prepare_bg_model(self.model_combo.currentText(), self.log.append, self.parent.language)
        if not model_path: return
        
        self.run_btn.setEnabled(False)
        self.prog.setValue(0)
        self.log.clear()
        
        self.worker = RemoveBGWorker(self.input_edit.text(), self.output_edit.text(), model_path)
        self.worker.progress.connect(self.prog.setValue)
        self.worker.log.connect(self.log.append)
        self.worker.finished.connect(lambda: self.run_btn.setEnabled(True))
        self.worker.start()