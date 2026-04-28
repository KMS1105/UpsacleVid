import os
import cv2
import openvino as ov
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QProgressBar, QTextEdit,
    QFileDialog
)
from PyQt5.QtCore import QThread, pyqtSignal
from setting import prepare_bg_model, DragLineEdit


class RemoveBGWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, input_path, output_path):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path

    def run(self):
        cap = None
        out = None

        try:
            self.log.emit("model_loading")
            core = ov.Core()

            model_paths = prepare_bg_model(lambda m: self.log.emit(m))
            if not model_paths:
                return

            def load(path):
                try:
                    return core.compile_model(path, "GPU.1")

                except:
                    try:
                        return core.compile_model(path, "GPU.0")

                    except:
                        return core.compile_model(path, "CPU")

            modnet = load(model_paths["modnet"])
            bisenet = load(model_paths["bisenet"])
            face_model = load(model_paths["face"])
            edge_model = load(model_paths["model_fp16"])

            cap = cv2.VideoCapture(self.input_path)
            w, h = int(cap.get(3)), int(cap.get(4))
            fps = cap.get(5)
            total = int(cap.get(7))

            output_file = os.path.join(self.output_path, "result.mp4")
            out = cv2.VideoWriter(output_file, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

            prev_alpha = None
            i = 0

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                img_m = cv2.resize(img, (1024, 1024)).astype(np.float32) / 255.0
                inp_m = img_m.transpose(2,0,1)[None]
                alpha = list(modnet([inp_m]).values())[0].squeeze()
                alpha = cv2.resize(alpha, (w, h))

                img_b = cv2.resize(img, (512, 512)).astype(np.float32)
                inp_b = img_b.transpose(2,0,1)[None]
                seg = list(bisenet([inp_b]).values())[0]
                seg = np.argmax(seg.squeeze(), axis=0)
                seg = cv2.resize(seg.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)

                person_classes = [1,2,3,4,5,6,7,8,9,10,11,12]
                bisenet_mask = np.isin(seg, person_classes).astype(np.float32)

                alpha = np.maximum(alpha, bisenet_mask * 0.7)

                face_inp = cv2.resize(frame, (672, 384))
                face_inp = face_inp.transpose(2,0,1)[None]
                detections = list(face_model([face_inp]).values())[0][0][0]

                for det in detections:
                    if det[2] > 0.5:
                        x1 = int(det[3] * w)
                        y1 = int(det[4] * h)
                        x2 = int(det[5] * w)
                        y2 = int(det[6] * h)

                        x1 = max(0,x1); y1 = max(0,y1)
                        x2 = min(w,x2); y2 = min(h,y2)

                        alpha[y1:y2, x1:x2] = np.maximum(alpha[y1:y2, x1:x2], 1.0)

                if prev_alpha is not None:
                    alpha = 0.95 * alpha + 0.05 * prev_alpha

                prev_alpha = alpha

                alpha = cv2.medianBlur((alpha*255).astype(np.uint8), 5)

                kernel = np.ones((5,5), np.uint8)
                alpha = cv2.morphologyEx(alpha, cv2.MORPH_OPEN, kernel)
                alpha = cv2.morphologyEx(alpha, cv2.MORPH_CLOSE, kernel)

                kernel_d = np.ones((7,7), np.uint8)
                alpha = cv2.dilate(alpha, kernel_d)
                alpha = alpha / 255.0

                img_e = cv2.resize(img, (1024, 1024)).astype(np.float32) / 255.0
                inp_e = img_e.transpose(2,0,1)[None]
                edge = list(edge_model([inp_e]).values())[0].squeeze()
                edge = cv2.resize(edge, (w, h))

                edge_mask = (alpha > 0.1) & (alpha < 0.9)
                alpha[edge_mask] = edge[edge_mask]
                alpha = cv2.GaussianBlur(alpha, (3,3), 0)
                alpha[alpha < 0.1] = 0
                alpha = np.clip(alpha, 0, 1)

                result = (frame * alpha[...,None]).astype(np.uint8)
                out.write(result)
                i += 1

                if i % 10 == 0 or i == total:
                    p = int(i * 100 / total)
                    self.progress.emit(p)
                    self.log.emit(f"processing {i}/{total} {p}%")

            self.log.emit("done")

        except Exception as e:
            self.log.emit(f"error {str(e)}")

        finally:
            if cap: cap.release()
            if out: out.release()
            self.finished.emit()

class RemoveBGTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        layout = QVBoxLayout(self)

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
        self.browse_out_btn.clicked.connect(lambda: self.output_edit.setText(QFileDialog.getExistingDirectory()))
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
        if not self.output_edit.text():
            return

        self.run_btn.setEnabled(False)
        self.prog.setValue(0)
        self.log.clear()

        self.worker = RemoveBGWorker(self.input_edit.text(), self.output_edit.text())
        self.worker.progress.connect(self.prog.setValue)
        self.worker.log.connect(self.log.append)
        self.worker.finished.connect(lambda: self.run_btn.setEnabled(True))
        self.worker.start()