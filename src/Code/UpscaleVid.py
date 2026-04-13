import sys
import os
import cv2
import torch
import numpy as np
import openvino as ov
import urllib.request
import subprocess
from collections import deque
from threading import Thread
from queue import Queue
import time
from openvino.runtime import Core, AsyncInferQueue
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QComboBox, QTextEdit, QProgressBar, QVBoxLayout
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt

def run_split_upscale(input_path, num_splits, target_parts, scale=2, tile=800, output_folder='./Vid', progress_callback=None, log_callback=None):
    core = ov.Core()
    available_devices = core.available_devices
    device_name = "CUDA" if torch.cuda.is_available() else ("GPU" if any("GPU" in d for d in available_devices) else "CPU")

    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet

    model_filenames = {2: 'RealESRGAN_x2plus', 4: 'RealESRGAN_x4plus', 8: 'RealESRGAN_x8'}
    model_urls = {
        2: 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
        4: 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth',
        8: 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRGAN_x8.pth'
    }
    
    model_base = model_filenames.get(scale, 'RealESRGAN_x2plus')
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    weights_dir = os.path.join(base_dir, 'weights')
    os.makedirs(weights_dir, exist_ok=True)
    pth_path = os.path.join(weights_dir, f"{model_base}.pth")
    xml_path = os.path.join(weights_dir, f"{model_base}.xml")

    if not os.path.exists(pth_path):
        if log_callback: log_callback(f"📥 모델 다운로드 중: {model_base}")
        urllib.request.urlretrieve(model_urls[scale], pth_path)

    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    new_h, new_w = (height // 4) * 4, (width // 4) * 4
    out_w, out_h = new_w * scale, new_h * scale

    if device_name == "GPU":
        gpu_id = "GPU.1" if "GPU.1" in available_devices else "GPU.0"
        if log_callback: log_callback(f"🚀 OpenVINO GPU 가속 사용: {gpu_id}")
        if not os.path.exists(xml_path):
            if log_callback: log_callback("⚙️ 모델 변환 중 (최초 1회)...")
            model_temp = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=scale)
            loadnet = torch.load(pth_path, map_location='cpu')
            model_temp.load_state_dict(loadnet['params_ema'] if 'params_ema' in loadnet else loadnet, strict=True)
            model_temp.eval()
            ov.save_model(ov.convert_model(model_temp, example_input=torch.randn(1, 3, 256, 256)), xml_path)
        
        ov_model_loaded = core.read_model(xml_path)
        ov_model_loaded.reshape([1, 3, new_h, new_w])
        compiled_model = core.compile_model(ov_model_loaded, gpu_id)
        infer_queue = AsyncInferQueue(compiled_model, 8)
        write_queue = Queue(maxsize=128)

        def completion_callback(infer_request, _):
            res = infer_request.get_output_tensor(0).data
            output = np.squeeze(res).clip(0, 1).transpose(1, 2, 0)
            output = cv2.cvtColor((output * 255.0).astype(np.uint8), cv2.COLOR_RGB2BGR)
            write_queue.put(output.tobytes())

        infer_queue.set_callback(completion_callback)
    else:
        if log_callback: log_callback(f"🖥️ {device_name} 모드로 실행")
        model_arch = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=scale)
        upsampler = RealESRGANer(scale=scale, model_path=pth_path, model=model_arch, tile=tile, half=(device_name=="CUDA"), device='cuda' if device_name=="CUDA" else 'cpu')
        write_queue = Queue(maxsize=128)

    frames_per_part = total_frames // num_splits
    parts_ranges = [(i * frames_per_part, (i + 1) * frames_per_part if i != num_splits - 1 else total_frames) for i in range(num_splits)]
    selected_parts = sorted([idx for idx in target_parts if 0 <= idx < num_splits])
    total_selected_frames = sum(parts_ranges[idx][1] - parts_ranges[idx][0] for idx in selected_parts)
    processed_count = 0

    video_filename = os.path.splitext(os.path.basename(input_path))[0]
    final_output_dir = os.path.join(output_folder, video_filename)
    os.makedirs(final_output_dir, exist_ok=True)
    part_files = []

    if log_callback: log_callback(f"🎬 총 {len(selected_parts)}개 파트 처리 시작 (형식: upscale{scale}x_n_{num_splits}.mov)")

    for part_idx in selected_parts:
        start_f, end_f = parts_ranges[part_idx]
        output_path = os.path.join(final_output_dir, f"upscale{scale}x_{part_idx}_{num_splits}.mov")
        part_files.append(output_path)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)

        start_time = start_f / fps
        duration = (end_f - start_f) / fps
        if log_callback: log_callback(f"📦 파트 {part_idx} 시작 ({start_f} ~ {end_f} 프레임)")

        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-f', 'rawvideo', '-vcodec', 'rawvideo', '-s', f'{out_w}x{out_h}', '-pix_fmt', 'bgr24', '-r', str(fps), '-i', '-', 
            '-ss', str(start_time), '-t', str(duration), '-accurate_seek', '-i', input_path,
            '-map', '0:v', '-map', '1:a?',
            '-c:v', 'h264_qsv', '-preset', 'veryfast', '-global_quality', '25',
            '-c:a', 'pcm_s16le', 
            '-af', 'aresample=async=1', 
            '-vsync', 'cfr',
            output_path
        ]
        process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)

        def writer_thread_func(proc, q):
            try:
                while True:
                    data = q.get()
                    if data is None: break
                    proc.stdin.write(data)
                proc.stdin.flush() 
                proc.stdin.close()
            except: pass

        w_thread = Thread(target=writer_thread_func, args=(process, write_queue), daemon=True)
        w_thread.start()

        input_queue = Queue(maxsize=32)
        def preprocessor_thread():
            for _ in range(start_f, end_f):
                ret, frame = cap.read()
                if not ret: break
                if device_name == "GPU":
                    img = cv2.resize(frame, (new_w, new_h))
                    inp = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
                    inp = inp.transpose(2, 0, 1)[np.newaxis, ...]
                    input_queue.put(inp)
                else:
                    input_queue.put(frame)
            input_queue.put(None)

        p_thread = Thread(target=preprocessor_thread, daemon=True)
        p_thread.start()

        while True:
            data = input_queue.get()
            if data is None: break
            if device_name == "GPU":
                infer_queue.start_async({0: data})
            else:
                output, _ = upsampler.enhance(data, outscale=scale)
                write_queue.put(output.tobytes())
            processed_count += 1
            if progress_callback:
                progress_callback(int(processed_count * 90 / total_selected_frames))
            if log_callback and processed_count % 200 == 0:
                log_callback(f"⏳ 진행 중: {processed_count}/{total_selected_frames} 프레임 완료")
        
        p_thread.join()
        if device_name == "GPU": infer_queue.wait_all()
        write_queue.put(None)
        w_thread.join()
        process.wait()
        if log_callback: log_callback(f"✅ 파트 {part_idx} 저장 완료: {os.path.basename(output_path)}")
    
    cap.release()
    
    if len(part_files) > 1:
        if log_callback: log_callback("🔗 최종 병합 및 오디오 인코딩 중...")
        list_path = os.path.join(final_output_dir, "parts.txt")
        with open(list_path, 'w', encoding='utf-8') as f:
            for p in part_files:
                safe_p = os.path.abspath(p).replace('\\', '/')
                f.write(f"file '{safe_p}'\n")
                
        start_p = selected_parts[0]
        end_p = selected_parts[-1]
        
        merged_path = os.path.join(final_output_dir, f"{video_filename}_full_{scale}x_{start_p}~{end_p}.mp4")
        merge_cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_path,
            '-c:v', 'copy', 
            '-c:a', 'aac', '-b:a', '192k', 
            merged_path
        ]
        subprocess.run(merge_cmd, capture_output=True)
        if os.path.exists(list_path): os.remove(list_path)
        if log_callback: log_callback(f"✨ 전체 병합 완료: {os.path.basename(merged_path)}")

    if progress_callback: progress_callback(100)
    return final_output_dir

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
            result_dir = run_split_upscale(
                self.input_path, self.num_splits, self.target_parts, 
                self.scale, self.tile, self.output_folder, 
                self.progress.emit, self.log.emit
            )
            self.finished.emit(f"✨ 완료: {os.path.abspath(result_dir)}")
        except Exception as e:
            self.finished.emit(f"❌ 오류 발생: {str(e)}")

def create_label_with_info(parent, text_key, tip_key):
    layout = QHBoxLayout()
    label = QLabel(parent.t(text_key))
    info_btn = QPushButton("?")
    info_btn.setFixedSize(20, 20)
    info_btn.setToolTip(parent.t(tip_key))
    info_btn.setStyleSheet("QPushButton { border-radius: 10px; background-color: #e0e0e0; font-weight: bold; }")
    layout.addWidget(label)
    layout.addWidget(info_btn)
    layout.addStretch()
    container = QWidget()
    container.setLayout(layout)
    return container

def create_video_tab(parent, translations):
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
    parent.split_spin.setRange(1, 999)
    parent.split_spin.setValue(10)
    split_layout.addWidget(parent.split_spin)
    layout.addLayout(split_layout)

    target_layout = QHBoxLayout()
    target_layout.addWidget(create_label_with_info(parent, 'target_parts', 'target_parts_tip'))
    parent.target_parts_edit = QLineEdit('0~9')
    target_layout.addWidget(parent.target_parts_edit)
    layout.addLayout(target_layout)

    tile_layout = QHBoxLayout()
    tile_layout.addWidget(create_label_with_info(parent, 'tile_size', 'tile_size_tip'))
    parent.tile_spin = QSpinBox()
    parent.tile_spin.setRange(0, 4096)
    parent.tile_spin.setValue(800)
    tile_layout.addWidget(parent.tile_spin)
    layout.addLayout(tile_layout)

    from setting import get_device_recommendation
    parent.vid_recommend_label = QLabel(get_device_recommendation(parent.language))
    layout.addWidget(parent.vid_recommend_label)

    parent.vid_progress = QProgressBar()
    layout.addWidget(parent.vid_progress)

    parent.vid_log = QTextEdit()
    parent.vid_log.setReadOnly(True)
    layout.addWidget(parent.vid_log)

    parent.vid_run_btn = QPushButton(parent.t('run_video_upscale'))
    parent.vid_run_btn.setFixedHeight(40)
    parent.vid_run_btn.clicked.connect(parent.run_video_upscale)
    layout.addWidget(parent.vid_run_btn)

    tab = QWidget()
    tab.setLayout(layout)
    return tab