import platform
import subprocess
import psutil
import sys
import urllib.request
import os
import time
import gc
import zipfile
import shutil
from UI_TEXTS import UI_TEXTS

MODEL_INFO = {
    2: {'name': 'RealESRGAN_x2plus', 'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth'},
    4: {'name': 'RealESRGAN_x4plus', 'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth'},
}

def prepare_ffmpeg(base_dir, log_func=None, progress_func=None):
    ffmpeg_dir = os.path.join(base_dir, "ffmpeg")
    
    if shutil.which("ffmpeg"):
        return True

    for root, dirs, files in os.walk(ffmpeg_dir):
        if "ffmpeg.exe" in files:
            bin_path = root
            if bin_path not in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + bin_path
            return True

    if log_func: log_func(f"[{time.strftime('%H:%M:%S')}] ⏳ FFmpeg not found, starting download...")
    os.makedirs(ffmpeg_dir, exist_ok=True)
    
    url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    zip_path = os.path.join(ffmpeg_dir, "ffmpeg.zip")
    
    try:
        def report_hook(block_num, block_size, total_size):
            if total_size > 0 and progress_func:  
                percent = int(block_num * block_size * 95 / total_size)
                if percent <= 95:
                    progress_func(percent)

        urllib.request.urlretrieve(url, zip_path, reporthook=report_hook)
        
        if log_func: log_func(f"[{time.strftime('%H:%M:%S')}] 📦 Decompressing...")
        if progress_func: progress_func(96) 
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        
        if progress_func: progress_func(100) 
        time.sleep(0.5) 
        
        new_bin_path = ""
        for root, dirs, files in os.walk(ffmpeg_dir):
            if "ffmpeg.exe" in files:
                new_bin_path = root
                break
        
        if new_bin_path:
            if new_bin_path not in os.environ["PATH"]:
                os.environ["PATH"] += os.pathsep + new_bin_path
            if os.path.exists(zip_path): os.remove(zip_path)
            return True
            
    except Exception as e:
        if log_func: log_func(f"[{time.strftime('%H:%M:%S')}] ❌ FFmpeg installation error: {str(e)}")
        if progress_func: progress_func(0)
        return False
        
    return False

def prepare_bg_model(model_name, log_func=None, lang='ko'):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    weights_dir = os.path.join(base_dir, 'RemBG')
    
    onnx_path = os.path.join(weights_dir, f"{model_name}.onnx")
    
    if os.path.exists(onnx_path):
        return onnx_path
    else:
        if log_func:
            log_func(f"❌ Error: {model_name}.onnx not found.")
        return None

def prepare_model(scale, weights_dir, log_func=None, lang='ko'):
    texts = UI_TEXTS.get(lang, UI_TEXTS['en'])
    if scale not in MODEL_INFO: return None, None
    if getattr(sys, 'frozen', False):
        if not weights_dir.endswith("src\\weights") and not weights_dir.endswith("src/weights"):
            weights_dir = os.path.join(weights_dir, "src", "weights")
    
    import torch
    import torch.onnx
    from basicsr.archs.rrdbnet_arch import RRDBNet
    
    model_data = MODEL_INFO[scale]
    pth_name = f"{model_data['name']}.pth"
    pth_path = os.path.join(weights_dir, pth_name)
    xml_path = pth_path.replace('.pth', '.xml')
    bin_path = pth_path.replace('.pth', '.bin')
    temp_onnx = os.path.join(weights_dir, f"temp_scale_{scale}.onnx")

    if not os.path.exists(pth_path):
        if log_func: log_func(f"⏳ {pth_name} Downloading...")
        os.makedirs(weights_dir, exist_ok=True)
        
        try:
            urllib.request.urlretrieve(model_data['url'], pth_path)
        except urllib.error.HTTPError as e:
            from PyQt5.QtWidgets import QMessageBox

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle(texts['err_conn_title'])
            msg.setText(texts['err_conn_text'])
            msg.setInformativeText(texts['err_conn_info'].format(e))
            msg.exec()
            
            return pth_path, None
            
        urllib.request.urlretrieve(model_data['url'], pth_path)
        if log_func: log_func("✅ Download complete")

    if not torch.cuda.is_available() and not os.path.exists(xml_path):
        if log_func:
            log_func("🔄 Converting model for Intel GPU acceleration (Scale x{scale})...")
        try:
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=scale)
            loadnet = None
            try:
                loadnet = torch.load(pth_path, map_location='cpu')
            except Exception:
                try:
                    loadnet = None
                    gc.collect()
                    time.sleep(2.0)
                    if os.path.exists(pth_path): os.remove(pth_path)
                    urllib.request.urlretrieve(model_data['url'], pth_path)
                    loadnet = torch.load(pth_path, map_location='cpu')
                except Exception as e:
                    if log_func: log_func("✅ Conversion completed: {0}".format(os.path.basename(xml_path)))
                    return pth_path, None

            key = 'params_ema' if 'params_ema' in loadnet else ('params' if 'params' in loadnet else None)
            state_dict = loadnet[key] if key else loadnet
            model.load_state_dict(state_dict, strict=True)
            model.eval()

            dummy_input = torch.randn(1, 3, 64, 64)
            torch.onnx.export(
                model, dummy_input, temp_onnx, 
                input_names=['input'], output_names=['output'],
                dynamic_axes={'input': {2: 'height', 3: 'width'}, 'output': {2: 'height', 3: 'width'}},
                opset_version=11
            )

            for _ in range(100):
                if os.path.exists(temp_onnx): break
                time.sleep(0.1)
            
            for _ in range(100):
                if os.path.exists(xml_path) and os.path.exists(bin_path):
                    if os.path.getsize(xml_path) > 0: break
                time.sleep(0.1)
            
            time.sleep(1.0)
            if os.path.exists(temp_onnx):
                try: os.remove(temp_onnx)
                except: pass
                
            if log_func: log_func("✅ Conversion completed: {0}".format(os.path.basename(xml_path)))
            
        except Exception as e:
            time.sleep(2.0)
            if os.path.exists(xml_path) and os.path.exists(bin_path):
                if log_func: 
                    log_func("✅ Conversion completed: {0}".format(os.path.basename(xml_path)))
                    if os.path.exists(temp_onnx):
                        try: os.remove(temp_onnx)
                        except: pass
            else:
                error_msg = str(e).strip()
                if not error_msg: 
                    error_msg = texts.get('log_unknown_opt_warn', 'Unknown error')
                
                if log_func: 
                    log_func(texts['log_convert_fail'].format(error_msg))
                return pth_path, None   
            
    return pth_path, (xml_path if os.path.exists(xml_path) else None)

def get_hardware_gpu_name():
    try:
        output = subprocess.check_output("wmic path win32_VideoController get name", shell=True).decode('utf-8')
        lines = [l.strip() for l in output.split('\n') if l.strip() and "Name" not in l]
        for line in lines:
            if "NVIDIA" in line or "GeForce" in line: return line
    except: pass
    return None

def get_detailed_system_info():
    try:
        cpu = platform.processor() or "Unknown CPU"
        mem = psutil.virtual_memory().total / (1024**3)
        gpu = "None"
        try:
            import torch
            if torch.cuda.is_available():
                gpu = torch.cuda.get_device_name(0)
            else:
                h_gpu = get_hardware_gpu_name()
                gpu = f"{h_gpu} (CUDA not supported)" if h_gpu else (get_intel_gpu_name() or "CPU")
        except:
            h_gpu = get_hardware_gpu_name()
            gpu = f"{h_gpu} (Library error)" if h_gpu else 'Torch not installed'
        return f"CPU: {cpu} | RAM: {mem:.1f}GB | GPU: {gpu}"
    except: return "Error"

def get_intel_gpu_name():
    try:
        if platform.system() == "Windows":
            cmd = "wmic path win32_VideoController get name"
            output = subprocess.check_output(cmd, shell=True).decode('utf-8')
            gpu_list = [line.strip() for line in output.split('\n') if "Intel" in line.strip()]
            if not gpu_list: return None
            for keyword in ["Arc", "Iris", "Intel"]:
                for gpu in gpu_list:
                    if keyword in gpu:
                        return gpu
    except:
        pass
    return None

def get_device_info_text(lang='ko'):
    import torch
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        return f"{UI_TEXTS[lang]['device_label']}GPU ({gpu_name})"
    intel_gpu = get_intel_gpu_name()
    if intel_gpu:
        return f"{UI_TEXTS[lang]['device_label']}Intel GPU ({intel_gpu})"
    cpu_name = platform.processor() or 'Unknown CPU'
    return f"{UI_TEXTS[lang]['device_label']}CPU ({cpu_name})"

def get_device_recommendation(lang='ko'):
    texts = UI_TEXTS[lang]
    import torch
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        lower_name = gpu_name.lower()
        if any(kw in lower_name for kw in ['rtx', 'a100', 'v100', 'titan', 'h100']):
            return texts['gpu_recommend_high'].format(gpu_name)
        if any(kw in lower_name for kw in ['gtx', '1660', '1080', '1070']):
            return texts['gpu_recommend_mid'].format(gpu_name)
        return texts['gpu_recommend_low'].format(gpu_name)
    intel_gpu = get_intel_gpu_name()
    if intel_gpu:
        return texts['igpu_recommend'].format(intel_gpu)
    cpu_name = platform.processor() or 'Unknown CPU'
    return texts['cpu_recommend'].format(cpu_name)

def format_time(seconds):
    if seconds is None or seconds < 0:
        return "--:--:--"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def apply_app_theme(widget, theme):
    if theme == 'dark':
        style = """
            QMainWindow { background-color: #121212; }
            QWidget { background-color: #1e1e1e; color: #e0e0e0; font-family: 'Malgun Gothic', sans-serif; font-size: 13px; }
            QToolTip { background-color: #333333; color: #ffffff; border: 1px solid #00bcff; border-radius: 4px; padding: 5px; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3e3e42; border-radius: 4px; padding: 5px; }
            QPushButton { background-color: #3a3a3a; color: #ffffff; border: 1px solid #505050; border-radius: 5px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #4a4a4a; border: 1px solid #007acc; }
            QProgressBar { background-color: #2d2d2d; border: 1px solid #3e3e42; border-radius: 8px; text-align: center; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #007acc, stop:1 #00bcff); border-radius: 7px; }
            QTabWidget::pane { border: 1px solid #3e3e42; background-color: #1e1e1e; top: -1px; }
            QTabBar::tab { background-color: #121212; color: #888888; padding: 12px 25px; border: 1px solid #3e3e42; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; }
            QTabBar::tab:selected { background-color: #1e1e1e; color: #00bcff; border-bottom: 3px solid #00bcff; font-weight: bold; }
            QListWidget { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3e3e42; }
            QLabel#timeline_title { 
                font-size: 16px; 
                font-weight: bold; 
                color: #00bcff !important; 
            }
        """
    else:
        style = """
            QMainWindow { background-color: #f5f5f7; }
            QWidget { background-color: #ffffff; color: #202124; font-family: 'Malgun Gothic', sans-serif; font-size: 13px; }
            QToolTip { background-color: #ffffff; color: #202124; border: 1px solid #dadce0; border-radius: 4px; padding: 8px; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox { background-color: #ffffff; color: #202124; border: 1px solid #dadce0; border-radius: 6px; padding: 5px; }
            QPushButton { background-color: #1a73e8; color: #ffffff; border: none; border-radius: 6px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #1a73e8; }
            QProgressBar { background-color: #e8eaed; border: 1px solid #dadce0; border-radius: 8px; text-align: center; color: #3c4043; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a73e8, stop:1 #4285f4); border-radius: 7px; }
            QTabWidget::pane { border: 1px solid #dadce0; background-color: #ffffff; top: -1px; }
            QTabBar::tab { background-color: #f1f3f4; color: #5f6368; padding: 12px 25px; border: 1px solid #dadce0; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; }
            QTabBar::tab:selected { background-color: #ffffff; color: #1a73e8; border-bottom: 3px solid #1a73e8; font-weight: bold; }
            QListWidget, QListView, QScrollArea, QAbstractScrollArea { background-color: #ffffff !important; color: #202124 !important; border: 1px solid #dadce0; }
            QListWidget::item { background-color: #ffffff; color: #202124; }
            QListWidget::item:selected { background-color: #e8f0fe; color: #1a73e8; }
            QGroupBox { border: 1px solid #dadce0; border-radius: 8px; margin-top: 10px; padding-top: 10px; background-color: #ffffff; }
            QLabel { background-color: transparent; color: #202124; }
            QLabel#timeline_title { 
                font-size: 16px !important; 
                font-weight: bold !important; 
                color: #00bcff !important; 
                background-color: transparent !important;
            }
            QLabel#source_title { 
                font-weight: bold !important; 
                background-color: transparent !important;
            }
        """
    widget.setStyleSheet(style)