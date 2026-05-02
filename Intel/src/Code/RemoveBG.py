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
from rembg import remove, new_session


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
            edge_model = None

            if "model_fp16" in model_paths:
                try:
                    edge_model = load(model_paths["model_fp16"])
                except:
                    edge_model = None

            cap = cv2.VideoCapture(self.input_path)
            w, h = int(cap.get(3)), int(cap.get(4))
            fps = cap.get(5)
            total = int(cap.get(7))

            output_file = os.path.join(self.output_path, "result.mp4")
            out = cv2.VideoWriter(output_file, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))

            try:
                os.environ["OMP_NUM_THREADS"] = "4"
                rembg_session = new_session("u2net", providers=["CPUExecutionProvider"])
            except:
                rembg_session = new_session()

            prev_alpha = None
            i = 0

            while i < total:
                ret, frame = cap.read()
                if not ret:
                    break

                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # ---------------- 1. 모델 추론 ----------------
                img_m = cv2.resize(img, (1024, 1024)).astype(np.float32) / 255.0
                inp_m = img_m.transpose(2, 0, 1)[None]
                alpha = list(modnet([inp_m]).values())[0].squeeze()
                alpha = cv2.resize(alpha, (w, h))

                rembg_result = remove(img, session=rembg_session)
                rembg_alpha = rembg_result[:, :, 3].astype(np.float32) / 255.0
                rembg_alpha = cv2.resize(rembg_alpha, (w, h))

                # 마스크 병합
                alpha = np.maximum(alpha, rembg_alpha * 0.8)
                alpha = np.clip(alpha, 0, 1)

                # ---------------- 2. 적응형 시간적 안정화 ----------------
                if prev_alpha is not None:
                    diff = np.abs(alpha - prev_alpha)
                    mean_diff = np.mean(diff)

                    if mean_diff > 0.05:
                        # [개선] 순간적인 큰 움직임 발생 시 이전 프레임의 잔상을 남기지 않고 즉각 반영
                        alpha = 0.85 * alpha + 0.15 * prev_alpha
                    else:
                        # 너무 크게 튀는 픽셀값만 이전 프레임 값으로 제한
                        alpha = np.where(diff > 0.35, prev_alpha, alpha)
                        alpha = 0.6 * alpha + 0.4 * prev_alpha

                # ---------------- 3. 공간적 평활화 및 얼룩 제거 ----------------
                kernel = np.ones((5, 5), np.uint8) # [개선] 커널 크기를 늘려 얼룩 제거 강화
                alpha_uint8 = (alpha * 255).astype(np.uint8)
                
                # 열림(Open) 연산 적용
                alpha_uint8 = cv2.morphologyEx(alpha_uint8, cv2.MORPH_OPEN, kernel)
                
                alpha = alpha_uint8.astype(np.float32) / 255.0
                alpha = cv2.GaussianBlur(alpha, (3, 3), 0)

                # ---------------- 4. edge refinement ----------------
                if edge_model is not None:
                    img_e = cv2.resize(img, (1024, 1024)).astype(np.float32) / 255.0
                    inp_e = img_e.transpose(2, 0, 1)[None]
                    edge = list(edge_model([inp_e]).values())[0].squeeze()
                    edge = cv2.resize(edge, (w, h))
                    edge_mask = (alpha > 0.05) & (alpha < 0.95)
                    alpha[edge_mask] = 0.85 * alpha[edge_mask] + 0.15 * edge[edge_mask]

                # ---------------- 5. hole filling ----------------
                alpha_uint8 = (alpha * 255).astype(np.uint8)
                alpha_uint8 = cv2.morphologyEx(alpha_uint8, cv2.MORPH_CLOSE, kernel)
                alpha = alpha_uint8.astype(np.float32) / 255.0

                # ---------------- 6. 최종 임계값 처리 ----------------
                # [개선] 얼룩 방지를 위해 0.35 이하의 반투명 값 강제 제거
                alpha[alpha < 0.35] = 0
                alpha = np.clip(alpha, 0, 1)

                # ---------------- 7. 최종 출력 ----------------
                result = (frame * alpha[..., None]).astype(np.uint8)
                out.write(result)

                prev_alpha = alpha.copy()
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