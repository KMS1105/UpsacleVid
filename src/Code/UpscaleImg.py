import os
import sys

try:
    import torchvision.transforms.functional as F
    sys.modules['torchvision.transforms.functional_tensor'] = F
except ImportError:
    pass

import cv2
import torch
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QProgressBar, QTextEdit, QVBoxLayout
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt

from setting import get_device_info_text, get_device_recommendation

class ImageUpscaleWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)

    def __init__(self, input_path, output_folder, scale):
        super().__init__()
        self.input_path = input_path
        self.output_folder = output_folder
        self.scale = scale

    def run(self):
        self.progress.emit(10)
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.progress.emit(20)

        model_urls = {
            2: 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
            4: 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth',
            8: 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRGAN_x8.pth'
        }
        model_url = model_urls.get(self.scale, model_urls[2])

        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer

        model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=23,
            num_grow_ch=32,
            scale=self.scale
        )
        self.progress.emit(30)

        upsampler = RealESRGANer(
            scale=self.scale,
            model_path=model_url,
            model=model,
            tile=0,
            tile_pad=10,
            pre_pad=0,
            half=(device.type == 'cuda'),
            device=device
        )
        self.progress.emit(40)

        img = cv2.imread(self.input_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            self.finished.emit(f"❌ 이미지를 찾을 수 없습니다: {self.input_path}")
            return

        self.progress.emit(60)
        try:
            output, _ = upsampler.enhance(img, outscale=self.scale)
            self.progress.emit(80)

            os.makedirs(self.output_folder, exist_ok=True)
            input_basename = os.path.splitext(os.path.basename(self.input_path))[0]
            output_file = os.path.join(self.output_folder, f"{input_basename}_upscaled_x{self.scale}.png")
            cv2.imwrite(output_file, output)
            self.progress.emit(100)
            self.finished.emit(f"✨ 완료! 결과가 저장되었습니다: {os.path.abspath(output_file)}")
        except Exception as e:
            self.finished.emit(f"❌ 처리 중 에러 발생: {e}")

def create_label_with_info(translator, text_key, tooltip_key):
    container = QWidget()
    hl = QHBoxLayout(container)
    hl.setContentsMargins(0, 0, 0, 0)
    
    label = QLabel(translator.t(text_key))
    
    info = QPushButton('?')
    info.setToolTip(translator.t(tooltip_key))
    
    info.setProperty("class", "help-button") 
    info.setFixedSize(20, 20)
    info.setCursor(Qt.PointingHandCursor)
    
    hl.addWidget(label)
    hl.addWidget(info)
    
    if hasattr(translator, 'translations'):
        translator.translations.append((label, 'setText', text_key))
        translator.translations.append((info, 'setToolTip', tooltip_key))
        
    return container

def create_image_tab(parent, translations):
    page = QWidget()
    layout = QVBoxLayout()

    input_layout = QHBoxLayout()
    input_layout.addWidget(create_label_with_info(parent, 'input_image', 'input_image_tip'))
    parent.img_input_edit = QLineEdit('')
    input_layout.addWidget(parent.img_input_edit)
    parent.img_browse_btn = QPushButton(parent.t('browse'))
    parent.img_browse_btn.clicked.connect(parent.browse_image_input)
    input_layout.addWidget(parent.img_browse_btn)
    layout.addLayout(input_layout)

    output_layout = QHBoxLayout()
    output_layout.addWidget(create_label_with_info(parent, 'output_folder', 'output_folder_tip'))
    parent.img_output_edit = QLineEdit('')
    output_layout.addWidget(parent.img_output_edit)
    parent.img_output_browse_btn = QPushButton(parent.t('browse'))
    parent.img_output_browse_btn.clicked.connect(parent.browse_output_folder)
    output_layout.addWidget(parent.img_output_browse_btn)
    layout.addLayout(output_layout)

    scale_layout = QHBoxLayout()
    scale_layout.addWidget(create_label_with_info(parent, 'scale', 'scale_tip'))
    parent.img_scale_combo = QComboBox()
    parent.img_scale_combo.addItems(['2x', '4x', '8x'])
    scale_layout.addWidget(parent.img_scale_combo)
    layout.addLayout(scale_layout)

    parent.img_device_label = QLabel(get_device_info_text(parent.language))
    layout.addWidget(parent.img_device_label)

    parent.img_recommend_label = QLabel(get_device_recommendation(parent.language))
    layout.addWidget(parent.img_recommend_label)

    parent.img_progress = QProgressBar()
    layout.addWidget(parent.img_progress)

    parent.img_run_btn = QPushButton(parent.t('upscale_image'))
    parent.img_run_btn.clicked.connect(parent.run_image_upscale)
    layout.addWidget(parent.img_run_btn)

    parent.img_log = QTextEdit()
    parent.img_log.setReadOnly(True)
    layout.addWidget(parent.img_log)

    page.setLayout(layout)
    return page