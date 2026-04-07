import sys
try:
    import torchvision.transforms.functional as F
    sys.modules['torchvision.transforms.functional_tensor'] = F
except ImportError:
    pass

import os
import cv2
import torch
from openvino.runtime import Core

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QComboBox, QTextEdit, QProgressBar, QVBoxLayout
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt

from setting import get_device_info_text, get_device_recommendation

def run_split_upscale(input_path, num_splits, target_parts, scale=2, tile=800, output_folder='./Vid', progress_callback=None, log_callback=None):
    ie = Core()
    devices = ie.available_devices
    
    if torch.cuda.is_available():
        device_name = "CUDA"
    elif any("GPU" in d for d in devices):
        device_name = "GPU"
    else:
        device_name = "CPU"

    if log_callback:
        log_callback(f"🚀 Acceleration: {device_name} (via OpenVINO)")

    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet

    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=scale)
    
    upsampler = RealESRGANer(
        scale=scale,
        model_path=None,
        model=model,
        tile=tile,
        half=False,
        device='cuda' if device_name == "CUDA" else 'cpu'
    )

    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Error: {input_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frames_per_part = total_frames // num_splits
    parts_ranges = []
    for i in range(num_splits):
        start = i * frames_per_part
        end = (i + 1) * frames_per_part if i != num_splits - 1 else total_frames
        parts_ranges.append((start, end))

    selected_parts = [idx for idx in target_parts if 0 <= idx < num_splits]
    if not selected_parts:
        cap.release()
        return

    os.makedirs(output_folder, exist_ok=True)
    total_selected_frames = sum(parts_ranges[idx][1] - parts_ranges[idx][0] for idx in selected_parts)
    processed_frames = 0

    for part_idx in selected_parts:
        start_f, end_f = parts_ranges[part_idx]
        output_path = os.path.join(output_folder, f"part_{part_idx}_x{scale}.mov")
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width * scale, height * scale))

        try:
            for frame_idx in range(start_f, end_f):
                ret, frame = cap.read()
                if not ret: break
                output, _ = upsampler.enhance(frame, outscale=scale)
                out.write(output)
                processed_frames += 1
                if progress_callback:
                    progress_callback(int(processed_frames * 100 / total_selected_frames))
        finally:
            out.release()

    cap.release()
    if progress_callback:
        progress_callback(100)

class VideoUpscaleWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, input_path, output_folder, num_splits, target_parts, tile, scale):
        super().__init__()
        self.input_path = input_path
        self.output_folder = output_folder
        self.num_splits = num_splits
        self.target_parts = target_parts
        self.tile = tile
        self.scale = scale

    def run(self):
        try:
            run_split_upscale(
                self.input_path, self.num_splits, self.target_parts,
                scale=self.scale, tile=self.tile, output_folder=self.output_folder,
                progress_callback=self.progress.emit, log_callback=self.log.emit
            )
            self.finished.emit("✨ Video upscaling completed.")
        except Exception as e:
            self.finished.emit(f"❌ Error: {e}")

def create_label_with_info(translator, text_key, tooltip_key):
    container = QWidget()
    hl = QHBoxLayout(container)
    hl.setContentsMargins(0, 0, 0, 0)
    
    label = QLabel(translator.t(text_key))
    
    info = QPushButton('?')
    info.setToolTip(translator.t(tooltip_key))
    info.setFixedSize(20, 20)
    info.setCursor(Qt.PointingHandCursor)
    
    hl.addWidget(label)
    hl.addWidget(info)
    
    if hasattr(translator, 'translations'):
        translator.translations.append((label, 'setText', text_key))
        translator.translations.append((info, 'setToolTip', tooltip_key))
        
    return container

def create_video_tab(parent, translations):
    page = QWidget()
    layout = QVBoxLayout()

    input_layout = QHBoxLayout()
    input_layout.addWidget(create_label_with_info(parent, 'input_video', 'input_video_tip'))
    parent.vid_input_edit = QLineEdit('')
    input_layout.addWidget(parent.vid_input_edit)
    parent.vid_browse_btn = QPushButton(parent.t('browse'))
    parent.vid_browse_btn.clicked.connect(parent.browse_video_input)
    input_layout.addWidget(parent.vid_browse_btn)
    layout.addLayout(input_layout)

    output_layout = QHBoxLayout()
    output_layout.addWidget(create_label_with_info(parent, 'output_folder', 'output_folder_tip'))
    parent.vid_output_edit = QLineEdit('')
    output_layout.addWidget(parent.vid_output_edit)
    parent.output_browse_btn = QPushButton(parent.t('browse'))
    parent.output_browse_btn.clicked.connect(parent.browse_output_folder)
    output_layout.addWidget(parent.output_browse_btn)
    layout.addLayout(output_layout)

    scale_layout = QHBoxLayout()
    scale_layout.addWidget(create_label_with_info(parent, 'scale', 'scale_tip'))
    parent.vid_scale_combo = QComboBox()
    parent.vid_scale_combo.addItems(['2x', '4x', '8x'])
    scale_layout.addWidget(parent.vid_scale_combo)
    layout.addLayout(scale_layout)

    split_layout = QHBoxLayout()
    split_layout.addWidget(create_label_with_info(parent, 'split_count', 'split_count_tip'))
    parent.split_spin = QSpinBox()
    parent.split_spin.setMinimum(1)
    parent.split_spin.setValue(10)
    split_layout.addWidget(parent.split_spin)
    layout.addLayout(split_layout)

    target_layout = QHBoxLayout()
    target_layout.addWidget(create_label_with_info(parent, 'target_parts', 'target_parts_tip'))
    parent.target_parts_edit = QLineEdit('0')
    target_layout.addWidget(parent.target_parts_edit)
    layout.addLayout(target_layout)

    tile_layout = QHBoxLayout()
    tile_layout.addWidget(create_label_with_info(parent, 'tile_size', 'tile_size_tip'))
    parent.tile_spin = QSpinBox()
    parent.tile_spin.setMinimum(0)
    parent.tile_spin.setMaximum(4096)
    parent.tile_spin.setValue(800)
    tile_layout.addWidget(parent.tile_spin)
    layout.addLayout(tile_layout)

    parent.vid_device_label = QLabel(get_device_info_text(parent.language))
    layout.addWidget(parent.vid_device_label)

    parent.vid_recommend_label = QLabel(get_device_recommendation(parent.language))
    layout.addWidget(parent.vid_recommend_label)

    parent.vid_progress = QProgressBar()
    layout.addWidget(parent.vid_progress)

    parent.vid_run_btn = QPushButton(parent.t('run_video_upscale'))
    parent.vid_run_btn.clicked.connect(parent.run_video_upscale)
    layout.addWidget(parent.vid_run_btn)

    parent.vid_log = QTextEdit()
    parent.vid_log.setReadOnly(True)
    layout.addWidget(parent.vid_log)

    page.setLayout(layout)
    return page