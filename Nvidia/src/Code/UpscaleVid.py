import sys
import os
import cv2
import torch
import numpy as np
import subprocess
import glob
import time
from threading import Thread
from queue import Queue, Empty
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QSpinBox, QComboBox, QTextEdit, 
    QProgressBar, QVBoxLayout, QSizePolicy)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from setting import UI_TEXTS

class ModelSetupWorker(QThread):
    log = pyqtSignal(str)
    finished = pyqtSignal()
    def __init__(self, weights_dir):
        super().__init__()
        self.weights_dir = weights_dir

def run_split_upscale(
    input_path, 
    num_splits, 
    target_parts, 
    model_path, 
    tile=800, 
    output_folder='./Vid', 
    progress_callback=None, 
    log_callback=None,
    lang='ko'
    ):
    
    import os
    import glob
    import shutil
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"log_model_not_found|{model_path}")
        
    tile = int(tile)
    num_splits = int(num_splits)
    model_name = os.path.splitext(os.path.basename(model_path))[0]
    scale = 2 if 'x2' in model_name.lower() else 8 if 'x8' in model_name.lower() else 4
    
    target_device = "CPU"
        
    if "GPU" in target_device:
        q_size = 32
        job_count = 1
    else:
        q_size = 64
        job_count = os.cpu_count() // 2

    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    orig_w, orig_h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    new_h, new_w = (orig_h // 8) * 8, (orig_w // 8) * 8
    write_queue = Queue(maxsize=q_size)
    processed_count = 0
    actual_out_w, actual_out_h = 0, 0 
    fatal_error = False
    
    def get_t(key): 
        return UI_TEXTS[lang].get(key, key)

    
    from realesrgan import RealESRGANer
    from basicsr.archs.rrdbnet_arch import RRDBNet
    model_arch = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=scale)
    upsampler = RealESRGANer(scale=scale, model_path=model_path, model=model_arch, tile=tile, half=torch.cuda.is_available(), device='cuda' if torch.cuda.is_available() else 'cpu')
    actual_out_w, actual_out_h = orig_w * scale, orig_h * scale

    frames_per_part = total_frames // num_splits
    parts_ranges = [(i * frames_per_part, (i + 1) * frames_per_part if i != num_splits - 1 else total_frames) for i in range(num_splits)]
    target_parts_validated = sorted([idx for idx in target_parts if 0 <= idx < num_splits])
    total_selected_frames = sum(parts_ranges[idx][1] - parts_ranges[idx][0] for idx in target_parts_validated)
    
    base_filename = os.path.splitext(os.path.basename(input_path))[0]
    final_output_dir = os.path.join(output_folder, base_filename)
    parts_dir = os.path.join(final_output_dir, f"{model_name}_parts")
    os.makedirs(parts_dir, exist_ok=True)
    
    temp_ts_files = []

    if log_callback:
        log_callback(f"log_res_optimized|{actual_out_w}x{actual_out_h}")

    for part_idx in target_parts_validated:
        if fatal_error:
            if log_callback: log_callback("log_fatal_error")
            break
            
        start_f, end_f = parts_ranges[part_idx]
        output_part_path = os.path.join(parts_dir, f"part_{part_idx + 1}.ts")
        
        if log_callback:
            log_callback(f"log_part_start|{part_idx + 1}|{num_splits}|{start_f}|{end_f}")
              
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)
        
        base_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ffmpeg_search = glob.glob(os.path.join(base_src, "**/ffmpeg.exe"), recursive=True)
            
        if ffmpeg_search:
            bin_path = [p for p in ffmpeg_search if 'bin' in p.lower()]
            ffmpeg_bin = bin_path[0] if bin_path else ffmpeg_search[0]
    
        else:
            print("❌ FFmpeg를 찾지 못했습니다. 시스템 기본값을 시도합니다.\n")
            ffmpeg_bin = 'ffmpeg'
            
        ffmpeg_cmd = [
            ffmpeg_bin, '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo', 
            '-s', f'{actual_out_w}x{actual_out_h}', '-pix_fmt', 'bgr24', '-r', str(fps), '-i', '-', 
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '18', 
            '-pix_fmt', 'yuv420p', '-an', '-sn', output_part_path
        ]
        
        process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

        def writer_thread_func(proc, q):
            while True:
                try:
                    data = q.get(timeout=2)
                    if data is None: break
                    proc.stdin.write(data)
                except Empty:
                    if proc.poll() is not None: break
            if proc.stdin: proc.stdin.close()
            proc.wait()

        w_thread = Thread(target=writer_thread_func, args=(process, write_queue), daemon=True)
        w_thread.start()

        def preprocessor_thread():
            nonlocal processed_count, fatal_error
            try:
                for _ in range(start_f, end_f):
                    if fatal_error: break
                    ret, frame = cap.read()
                    if not ret: break
                    img = cv2.resize(frame, (new_w, new_h))
                    
                    output, _ = upsampler.enhance(img, outscale=scale)
                    write_queue.put(output.tobytes())
                    processed_count += 1
                    if progress_callback: progress_callback(min(90, int(processed_count * 90 / total_selected_frames)))

            except Exception as e:
                fatal_error = True
                if log_callback: log_callback(f"log_error|{e}")
            finally:
                write_queue.put(None)

        p_thread = Thread(target=preprocessor_thread, daemon=True)
        p_thread.start()
        p_thread.join()
        w_thread.join()
        
        if os.path.exists(output_part_path) and os.path.getsize(output_part_path) > 0:
            temp_ts_files.append(output_part_path)
            if log_callback: log_callback(f"log_parts_saved|{part_idx + 1}")
    
    cap.release()

    if not fatal_error and len(temp_ts_files) == len(target_parts_validated):
        if log_callback: log_callback("log_merge_start")
        final_merged_path = os.path.join(final_output_dir, f"Final_{base_filename}_{model_name}.mp4")
        list_file_path = os.path.join(parts_dir, "join_list.txt")
        with open(list_file_path, "w", encoding="utf-8") as f:
            for ts_file in temp_ts_files:
                f.write(f"file '{os.path.abspath(ts_file)}'\n")
        
        merge_cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file_path,
            '-i', input_path, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
            '-map', '0:v', '-map', '1:a?', '-vsync', 'cfr', '-f', 'mp4', final_merged_path
        ]
        subprocess.run(merge_cmd, stderr=subprocess.DEVNULL)
        if os.path.exists(list_file_path): os.remove(list_file_path)
        if log_callback:
            log_callback(f"log_parts_saved|{parts_dir}")
            log_callback("log_upscale_complete")
        
    if progress_callback: progress_callback(100)
    return final_output_dir

class VideoUpscaleWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(str)
    def __init__(self, input_path, output_folder, num_splits, target_parts, tile, model_path):
        super().__init__()
        self.input_path, self.output_folder, self.num_splits = input_path, output_folder, num_splits
        self.target_parts, self.tile, self.model_path = target_parts, tile, model_path
    def run(self):
        try:
            res = run_split_upscale(self.input_path, self.num_splits, self.target_parts, self.model_path, self.tile, self.output_folder, self.progress.emit, self.log.emit)
            self.finished.emit(f"log_upscale_complete|{os.path.abspath(res)}")
        except Exception as e: self.finished.emit(f"log_error|{str(e)}")

def create_label_with_info(parent, text_key, tip_key):
    layout = QHBoxLayout()
    btn = QPushButton("?")
    btn.setFixedSize(20, 20)
    btn.setToolTip(parent.t(tip_key))
    btn.setStyleSheet("""
        QPushButton { 
            border-radius: 10px; 
            background-color: #e0e0e0; 
            color: #202124#ffffff; 
            font-weight: bold; 
            border: None;
        }
        QPushButton:hover { 
            background-color: #1a73e8; 
            color: #ffffff;           
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

def create_video_tab(parent, translations):
    layout = QVBoxLayout()
    weights_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'weights')
    os.makedirs(weights_dir, exist_ok=True)

    for key, edit_attr, btn_attr, click_func in [
        ('input_video', 'vid_input_edit', 'vid_browse_btn', parent.browse_video_input), 
        ('output_folder', 'vid_output_edit', 'vid_output_browse_btn', parent.browse_output_folder)
    ]:
        row = QHBoxLayout()
        container = create_label_with_info(parent, key, f"{key}_tip")
        
        label_obj = container.label_obj
        label_obj.text_key = key
        
        if key == 'input_video': 
            parent.vid_input_label = container.label_obj
        else: 
            parent.vid_output_label = container.label_obj
        row.addWidget(container)
        
        edit = QLineEdit()
        setattr(parent, edit_attr, edit)
        row.addWidget(edit)
        
        new_btn = QPushButton(parent.t('browse'))
        new_btn.text_key = 'browse'  
        setattr(parent, btn_attr, new_btn)
        parent.layout().addWidget(new_btn)
        getattr(parent, btn_attr).clicked.connect(click_func)
        row.addWidget(new_btn)
        layout.addLayout(row)

    model_row = QHBoxLayout()
    model_container = create_label_with_info(parent, 'model_select', 'model_select_tip')
    parent.vid_model_label = model_container.label_obj 
    model_row.addWidget(model_container)
    parent.vid_model_combo = QComboBox()
    parent.vid_model_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    
    def refresh_v_models():
        parent.vid_model_combo.clear()
        use_cuda = torch.cuda.is_available()
        pats = ["*.pth"] if use_cuda else ["*.onnx", "*.xml"]
        files = []
        for p in pats: 
            files.extend(glob.glob(os.path.join(weights_dir, "**", p), recursive=True))
        for f in files: 
            parent.vid_model_combo.addItem(os.path.relpath(f, weights_dir), f)
            
        if hasattr(parent, 'vid_log'):
            log_msg = "🔄 모델 목록이 갱신되었습니다." if parent.language == 'ko' else "🔄 Model list refreshed."
            parent.vid_log.append(log_msg)
        
    refresh_v_models()
    model_row.addWidget(parent.vid_model_combo)
    btn_refresh = QPushButton("🔄")
    btn_refresh.setFixedSize(30, 30)
    btn_refresh.clicked.connect(refresh_v_models)
    model_row.addWidget(btn_refresh)
    layout.addLayout(model_row)

    for key, spin_attr, val in [('split_count', 'vid_split_spin', 10), ('tile_size', 'vid_tile_spin', 800)]:
        row = QHBoxLayout()
        container = create_label_with_info(parent, key, f"{key}_tip")
        if key == 'split_count': 
            parent.vid_split_label = container.label_obj
        else: 
            parent.vid_tile_label = container.label_obj
        row.addWidget(container)
        
        setattr(parent, spin_attr, QSpinBox())
        getattr(parent, spin_attr).setRange(0, 4096)
        getattr(parent, spin_attr).setValue(val)
        row.addWidget(getattr(parent, spin_attr))
        layout.addLayout(row)

    target_row = QHBoxLayout()
    target_container = create_label_with_info(parent, 'target_parts', 'target_parts_tip')
    parent.vid_target_label = target_container.label_obj
    target_row.addWidget(target_container)
    parent.target_parts_edit = QLineEdit('0~9')
    target_row.addWidget(parent.target_parts_edit)
    layout.addLayout(target_row)
    
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
