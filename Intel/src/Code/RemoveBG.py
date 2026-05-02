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

rvm_weights_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
u2net_dir = os.path.join(rvm_weights_dir, 'RemBG')
os.environ["HF_HOME"] = rvm_weights_dir
os.environ["U2NET_HOME"] = u2net_dir


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

            # 모델 로딩 설정
            rvm_model_path = os.path.join(rvm_weights_dir, "robust-video-matting-mobilenetv3")
            model_paths = prepare_bg_model(lambda m: self.log.emit(m))
            
            def load(path):
                try: return core.compile_model(path, "GPU.1")
                except:
                    try: return core.compile_model(path, "GPU.0")
                    except: return core.compile_model(path, "CPU")

            rvm_model = load(rvm_model_path) if os.path.exists(rvm_model_path) else \
                        (load(model_paths["modnet"]) if model_paths and "modnet" in model_paths else None)
            
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
            prev_hsv = None
            i = 0

            while i < total:
                ret, frame = cap.read()
                if not ret: break

                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                # 1. 모델 추론 (MODNet 허용 범위 0.2로 확장 적용)
                main_alpha = None
                if rvm_model:
                    inp = cv2.resize(img_rgb, (1024, 1024)).astype(np.float32) / 255.0
                    inp = inp.transpose(2, 0, 1)[None]
                    res = list(rvm_model([inp]).values())
                    main_alpha = res[1].squeeze() if len(res) > 1 else res[0].squeeze()
                    main_alpha = cv2.resize(main_alpha, (w, h))

                res_rembg = remove(img_rgb, session=rembg_session)
                rembg_alpha = cv2.resize(res_rembg[:, :, 3].astype(np.float32) / 255.0, (w, h))

                confidence = np.abs(rembg_alpha - main_alpha) if main_alpha is not None else np.zeros_like(rembg_alpha)

                if main_alpha is not None:
                    current_alpha = np.where((main_alpha > 0.20) & (rembg_alpha > 0.20), rembg_alpha, np.maximum(main_alpha, rembg_alpha))
                else:
                    current_alpha = rembg_alpha

                current_alpha = np.clip(current_alpha, 0, 1)

                # 2. 채도 및 명도 기반 연속성 분석
                alpha_influence = 0.3
                if prev_hsv is not None:
                    diff_hsv = cv2.absdiff(img_hsv, prev_hsv)
                    s_diff = np.mean(diff_hsv[:, :, 1]) / 255.0
                    v_diff = np.mean(diff_hsv[:, :, 2]) / 255.0
                    if (s_diff + v_diff) < 0.05:
                        alpha_influence = 0.7

                if prev_alpha is not None:
                    alpha = (1.0 - alpha_influence) * current_alpha + alpha_influence * prev_alpha
                else:
                    alpha = current_alpha

                # 3. 이진화 (반투명 얼룩 방지)
                alpha = np.where(alpha >= 0.5, 1.0, 0.0)

                # 4. 테두리 추출
                alpha_u8 = (alpha * 255).astype(np.uint8)
                edges = cv2.Canny(alpha_u8, 100, 200)
                edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

                # 5. 닫힌/열린 테두리 분석
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                mask_for_fill = np.zeros_like(alpha_u8)

                for cnt in contours:
                    perimeter = cv2.arcLength(cnt, True)
                    if perimeter > 0:
                        # 튜플 타입 오류가 발생하지 않도록 isContourConvex 및 기본 면적/둘레 조건으로만 판단하도록 수정
                        approx = cv2.approxPolyDP(cnt, 0.02 * perimeter, True)
                        is_closed = cv2.isContourConvex(approx) or (cv2.contourArea(cnt) > 50)
                        
                        if is_closed:
                            cv2.drawContours(mask_for_fill, [cnt], -1, 1, thickness=-1)

                alpha = np.where(mask_for_fill > 0, 1.0, alpha)

                # 6. 결과 합성 및 테두리 색상 처리
                result = (frame * alpha[..., None]).astype(np.uint8)

                edge_y, edge_x = np.where(edges > 0)
                for ey, ex in zip(edge_y, edge_x):
                    if confidence[ey, ex] > 0.3:
                        result[ey, ex] = [0, 0, 255] # Red
                    else:
                        result[ey, ex] = [255, 255, 0] # Cyan

                out.write(result)
                
                prev_alpha = alpha
                prev_hsv = img_hsv
                i += 1
                if i % 10 == 0 or i == total:
                    self.progress.emit(int(i * 100 / total))

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