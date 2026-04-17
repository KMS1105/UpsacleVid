import sys
import os
import cv2
import torch
import numpy as np
import openvino as ov
import urllib.request
import glob
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QProgressBar, QTextEdit, QVBoxLayout, QApplication, QSpinBox, QSizePolicy
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from setting import get_device_info_text, get_device_recommendation, prepare_model

try:
    import torchvision.transforms.functional as F
    sys.modules['torchvision.transforms.functional_tensor'] = F
except ImportError:
    pass

class ModelSetupWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()
    def __init__(self, weights_dir):
        super().__init__()
        self.weights_dir = weights_dir
    def run(self):
        for scale in [2, 4]:
            prepare_model(scale, self.weights_dir, self.log.emit)
        self.finished.emit()

class ImageUpscaleWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(str)
    def __init__(self, input_path, output_folder, model_path, tile_size):
        super().__init__()
        self.input_path = input_path
        self.output_folder = output_folder
        self.model_path = model_path
        self.tile_size = tile_size
    def run(self):
        try: 
            self.progress.emit(10)
            core = ov.Core()
            available_devices = core.available_devices
            model_name = os.path.splitext(os.path.basename(self.model_path))[0]
            scale = 2 if 'x2' in model_name.lower() else 4
            img_array = np.fromfile(self.input_path, np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img is None: raise Exception("이미지를 읽을 수 없습니다.")
            use_cuda = torch.cuda.is_available()
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
            if not use_cuda and (self.model_path.endswith('.xml') or self.model_path.endswith('.onnx')):
                target_device = "GPU.1" if "GPU.1" in available_devices else "GPU.0" if "GPU.0" in available_devices else "CPU"
                h, w = img.shape[:2]
                new_h, new_w = (h // 4) * 4, (w // 4) * 4
                img_input = cv2.resize(img, (new_w, new_h))
                ov_model = core.read_model(self.model_path)
                ov_model.reshape([1, 3, new_h, new_w])
                compiled_model = core.compile_model(ov_model, target_device)
                input_data = cv2.cvtColor(img_input, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                input_data = input_data.transpose(2, 0, 1)[np.newaxis, ...]
                res = compiled_model(input_data)[compiled_model.output(0)]
                output = np.squeeze(res).clip(0, 1).transpose(1, 2, 0)
                output = cv2.cvtColor((output * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR)
            else:
                model_arch = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=scale)
                upsampler = RealESRGANer(scale=scale, model_path=self.model_path, model=model_arch, tile=self.tile_size, half=use_cuda, device='cuda' if use_cuda else 'cpu')
                output, _ = upsampler.enhance(img, outscale=scale)
            if not os.path.exists(self.output_folder): os.makedirs(self.output_folder)
            save_path = os.path.join(self.output_folder, f"up_{model_name}_{os.path.basename(self.input_path)}")
            res, en_img = cv2.imencode(os.path.splitext(save_path)[1], output)
            if res: en_img.tofile(save_path)
            self.progress.emit(100)
            self.finished.emit(f"✨ 업스케일 완료")
        except Exception as e:
            self.finished.emit(f"❌ 오류: {str(e)}")

def create_label_with_info(parent, text_key, tip_key):
    layout = QHBoxLayout()
    btn = QPushButton("?")
    btn.setFixedSize(20, 20)
    btn.setToolTip(parent.t(tip_key))
    btn.setStyleSheet("""
        QPushButton { 
            border-radius: 10px; 
            background-color: #1a73e8; 
            color: #ffffff; 
            font-weight: bold; 
            border: None;
        }
        QPushButton:hover { 
            background-color: #e0e0e0; 
            color: #202124;           
        }
    """)
    
    label = QLabel(parent.t(text_key))
    layout.addWidget(label)
    layout.addWidget(btn)
    layout.addStretch()
    
    container = QWidget()
    container.setLayout(layout)
    container.label_obj = label
    return container

def create_image_tab(parent, translations):
    layout = QVBoxLayout()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    weights_dir = os.path.join(base_dir, 'weights')
    os.makedirs(weights_dir, exist_ok=True)

    input_layout = QHBoxLayout()
    input_container = create_label_with_info(parent, 'input_image', 'input_image_tip')
    parent.img_input_label = input_container.label_obj
    input_layout.addWidget(input_container)
    
    parent.img_input_edit = QLineEdit('')
    input_layout.addWidget(parent.img_input_edit)
    parent.img_browse_btn = QPushButton(parent.t('browse'))
    parent.img_browse_btn.clicked.connect(parent.browse_image_input)
    input_layout.addWidget(parent.img_browse_btn)
    layout.addLayout(input_layout)

    output_layout = QHBoxLayout()
    output_container = create_label_with_info(parent, 'output_folder', 'output_folder_tip')
    parent.img_output_label = output_container.label_obj
    output_layout.addWidget(output_container)
    
    parent.img_output_edit = QLineEdit('')
    output_layout.addWidget(parent.img_output_edit)
    parent.img_output_browse_btn = QPushButton(parent.t('browse'))
    parent.img_output_browse_btn.clicked.connect(parent.browse_output_folder)
    output_layout.addWidget(parent.img_output_browse_btn)
    layout.addLayout(output_layout)

    model_sel_layout = QHBoxLayout()
    model_container = create_label_with_info(parent, 'model_select', 'model_select_tip')
    parent.img_model_label = model_container.label_obj
    model_sel_layout.addWidget(model_container)
    
    parent.img_model_combo = QComboBox()
    parent.img_model_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def refresh_models():
        parent.img_model_combo.clear()
        use_cuda = torch.cuda.is_available()
        patterns = ["*.pth"] if use_cuda else ["*.onnx", "*.xml"]
        files = []
        for p in patterns:
            files.extend(glob.glob(os.path.join(weights_dir, "**", p), recursive=True))
        for f in files:
            parent.img_model_combo.addItem(os.path.relpath(f, weights_dir), f)
            
        if hasattr(parent, 'img_log'):
            log_msg = "🔄 모델 목록이 갱신되었습니다." if parent.language == 'ko' else "🔄 Model list refreshed."
            parent.img_log.append(log_msg)

    model_sel_layout.addWidget(parent.img_model_combo)
    
    btn_refresh = QPushButton("🔄")
    btn_refresh.setFixedSize(30, 30)
    btn_refresh.clicked.connect(refresh_models)
    model_sel_layout.addWidget(btn_refresh)
    
    refresh_models()

    tile_container = create_label_with_info(parent, 'tile_size', 'tile_size_tip')
    parent.img_tile_label = tile_container.label_obj
    model_sel_layout.addWidget(tile_container)
    
    parent.img_tile_spin = QSpinBox()
    parent.img_tile_spin.setRange(0, 1024)
    parent.img_tile_spin.setValue(400)
    parent.img_tile_spin.setSingleStep(100)
    model_sel_layout.addWidget(parent.img_tile_spin)
    layout.addLayout(model_sel_layout)

    from setting import get_device_recommendation
    parent.img_recommend_label = QLabel(get_device_recommendation(parent.language))
    layout.addWidget(parent.img_recommend_label)
    
    parent.img_progress = QProgressBar()
    layout.addWidget(parent.img_progress)
    parent.img_log = QTextEdit()
    parent.img_log.setReadOnly(True)
    layout.addWidget(parent.img_log)

    parent.img_run_btn = QPushButton(parent.t('upscale_image'))
    parent.img_run_btn.setFixedHeight(40)

    def start_upscale():
        input_path = parent.img_input_edit.text()
        output_folder = parent.img_output_edit.text()
        model_path = parent.img_model_combo.currentData()
        tile_size = parent.img_tile_spin.value()
        if not input_path or not os.path.exists(input_path): return
        parent.img_run_btn.setEnabled(False)
        parent.img_worker = ImageUpscaleWorker(input_path, output_folder, model_path, tile_size)
        parent.img_worker.progress.connect(parent.img_progress.setValue)
        parent.img_worker.log.connect(parent.img_log.append)
        parent.img_worker.finished.connect(parent.on_image_finished)
        parent.img_worker.start()

    parent.img_run_btn.clicked.connect(start_upscale)
    layout.addWidget(parent.img_run_btn)

    parent.setup_worker = ModelSetupWorker(weights_dir)
    parent.setup_worker.log.connect(parent.img_log.append)
    parent.setup_worker.finished.connect(refresh_models)
    QTimer.singleShot(500, parent.setup_worker.start)

    tab = QWidget()
    tab.setLayout(layout)
    return tab