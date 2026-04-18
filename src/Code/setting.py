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

def prepare_model(scale, weights_dir, log_func=None, lang='ko'):
    texts = UI_TEXTS.get(lang, UI_TEXTS['en'])
    if scale not in MODEL_INFO: return None, None
    if getattr(sys, 'frozen', False):
        if not weights_dir.endswith("src\\weights") and not weights_dir.endswith("src/weights"):
            weights_dir = os.path.join(weights_dir, "src", "weights")
    
    import torch
    import openvino as ov
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
            from PySide6.QtWidgets import QMessageBox 

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

            ov_model = ov.convert_model(temp_onnx)
            ov.save_model(ov_model, xml_path)
            
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

def get_torch_install_command():
    gpu_name = get_hardware_gpu_name()
    if not gpu_name: return None
    
    if any(x in gpu_name for x in ["RTX 40", "RTX 50", "L4", "H100"]):
        url = "https://download.pytorch.org/whl/cu121"
    else:
        url = "https://download.pytorch.org/whl/cu118"
    
    return f"install torch torchvision torchaudio --index-url {url}"

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

UI_TEXTS = {
    'ko': {
        'window_title': '영상/이미지 업스케일러',
        'tab_image': '이미지 업스케일',
        'tab_video': '비디오 업스케일',
        'tab_video_merge': '영상 병합',
        'browse': '찾아보기',
        'model_select_tip': 'src/weights 안의 모델 중 하나를 선택하세요.',
        'output_folder': '출력 폴더:',
        'output_folder_tip': '결과물이 저장될 폴더를 선택합니다.',
        'device_label': '시스템 정보:',
        'input_image': '입력 이미지:',
        'input_image_tip': '업스케일할 이미지 파일을 선택하세요.',
        'upscale_image': '이미지 업스케일 시작',
        'model_select': '모델 선택:',
        'tile_size': '타일 크기:',
        'tile_size_tip': 'VRAM이 부족할 경우 타일 크기를 낮추세요.',
        'input_video': '입력 비디오:',
        'input_video_tip': '업스케일할 영상 파일을 선택하세요.',
        'run_video_upscale': '비디오 업스케일 시작',
        'split_count': '분할 개수:',
        'split_count_tip': '영상을 여러 파트로 나누어 처리합니다.',
        'target_parts': '대상 파트:',
        'target_parts_tip': '처리할 파트 번호를 입력하세요 (예: 0~9).',
        'input_folder': '입력 폴더:',
        'input_folder_tip': '합칠 영상 조각들이 들어있는 폴더를 선택하세요.',
        'audio_file': '오디오 파일:',
        'audio_file_tip': '배경음악 또는 원본 오디오를 선택하세요.',
        'select_folder': '폴더 선택',
        'select_audio': '오디오 선택',
        'clear_audio': '초기화',
        'work_list': '🎬 작업 목록',
        'run_merge': '영상 병합 실행',
        'menu_theme': '테마',
        'menu_light': '라이트 모드',
        'menu_dark': '다크 모드',
        'menu_language': '언어',
        'lang_ko': '한국어',
        'lang_en': '영어',
        'cpu_recommend': '[CPU 모드] {0} 사용 중. 2x 권장 및 분할 개수를 높이세요.',
        'igpu_recommend': '[Intel QSV 가속] {0} 사용 중. 2x 권장, 타일 200~400 조절.',
        'gpu_recommend_high': 'GPU: {0} - 권장: 2x/4x 사용, 타일 400~600 권장.',
        'gpu_recommend_mid': 'GPU: {0} - 권장: 2x 사용, 타일 200~300 권장.',
        'gpu_recommend_low': 'GPU: {0} - 권장: 2x 사용, 타일 100~200 권장.',
        'log_ffmpeg_start': "⏳ FFmpeg가 없어 다운로드를 시작합니다...",
        'log_extracting': "📦 압축 해제 중",
        'log_ffmpeg_error': "❌ FFmpeg 설치 오류: {}",
        'log_ffmpeg_ready': "✅ FFmpeg 준비 완료",
        'log_ffmpeg_fail': "❌ FFmpeg 초기 준비 실패",
        'log_downloading_model': "⏳ {} 다운로드 중...",
        'log_download_complete': "✅ 다운로드 완료",
        'log_converting_model': "🔄 Intel GPU 가속 모델 변환 중 (Scale x{})...",
        'log_convert_complete': "✅ 변환 완료: {}",
        'log_convert_fail': "❌ 변환 실패: {}",
        'log_upscale_complete': "✨ 업스케일 완료",
        'log_error': "❌ 오류: {}",
        'log_device_info': "🚀 가속 장치: {}",
        'log_model_info': "📦 모델: {}",
        'log_res_optimized': "✅ 해상도 최적화 완료: {}x{}",
        'log_parts_saved' : '📁 파트 {} 저장 완료',
        'log_fatal_error': "🛑 하드웨어 오류로 인해 작업을 즉시 중단합니다.",
        'log_part_start': "🎬 파트 {}/{} 시작 (프레임 {}~{})",
        'log_merge_start': "🔄 모든 파트 병합 및 오디오 합성 시작...",
        'log_audio_source': "🔊 소리 소스: {}",
        'log_audio_none': "🔊 소리 선택 해제 (무음 병합)",
        'log_merge_fail': "❌ 병합 실패",
        'lang_name': "한국어",
        'log_lang_changed': "🌐 언어가 변경되었습니다: {}",
        'err_input_title': '입력 오류',
        'err_input_msg': '입력 파일을 선택해주세요.',
        'err_part_title': '입력 오류',
        'err_part_msg': '대상 파트 형식이 올바르지 않습니다. (예: 0~9)',
        'log_files_found': '📁 {0}개 파일을 순서대로 찾았습니다.',
        'log_file_item': ' -> {0}',
        'warn_no_video_title': '경고',
        'warn_no_video_msg': '해당 폴더에 영상 파일이 없습니다.',
        'warn_no_folder_title': '경고',
        'warn_no_folder_msg': '먼저 병합할 폴더를 선택해주세요.',
        'save_dialog_title': '결과 저장',
        'save_dialog_filter': 'MP4 파일 (*.mp4);;TS 파일 (*.ts)',
        'log_merge_success': '✅ 완료: {0}',
        'log_merge_fail': '❌ 실패: {0}',
        'msg_merge_success_title': '완료',
        'msg_merge_success_text': '영상 병합이 성공적으로 끝났습니다.',
        'msg_merge_fail_title': '오류',
        'msg_merge_fail_text': '병합 중 오류가 발생했습니다: {0}',
        'log_convert_success': '✅ 변환 완료: {0}',
        'log_convert_fail': '❌ 변환 실패: {0}',
        'log_unknown_opt_warn': '알 수 없는 최적화 경고',
        'log_file_replace_fail': '❌ 파일 교체 실패: {0}',
        'log_intel_convert': '🔄 Intel GPU 가속 모델 변환 중 (Scale x{0})...',
        'log_download_complete': '✅ 다운로드 완료',
        'err_conn_title': '연결 오류',
        'err_conn_text': '다운로드 실패 (Time-out)',
        'err_conn_info': '네트워크 문제로 모델을 다운로드할 수 없습니다.\n\n오류 내용: {0}\n\n프로그램을 다시 실행해주세요.',
        'audio_select_title': '오디오 파일 선택',
        'audio_select_filter': '오디오 파일 (*.mp3 *.wav *.aac *.m4a);;영상 파일 (*.mp4 *.mov *.avi *.mkv)',
        'log_audio_source': '🎵 오디오 소스 설정됨: {0}',
    },
    'en': {
        'window_title': 'Image/Video Upscaler',
        'tab_image': 'Image Upscale',
        'tab_video': 'Video Upscale',
        'tab_video_merge': 'Video Auto Merge',
        'browse': 'Browse',
        'model_select_tip': 'Please select one of the models in src/weights.',
        'output_folder': 'Output Folder:',
        'output_folder_tip': 'Select output folder.',
        'device_label': 'System Info:',
        'input_image': 'Input Image:',
        'input_image_tip': 'Select image to upscale.',
        'upscale_image': 'Start Image Upscale',
        'model_select': 'Select Model:',
        'tile_size': 'Tile Size:',
        'tile_size_tip': 'Lower tile size if VRAM is low.',
        'input_video': 'Input Video:',
        'input_video_tip': 'Select video to upscale.',
        'run_video_upscale': 'Start Video Upscale',
        'split_count': 'Split Count:',
        'split_count_tip': 'Splits video for parallel processing.',
        'target_parts': 'Target Parts:',
        'target_parts_tip': 'Enter parts (e.g., 0~9).',
        'input_folder': 'Input Folder:',
        'input_folder_tip': 'Select folder with video parts.',
        'audio_file': 'Audio File:',
        'audio_file_tip': 'Select audio file.',
        'select_folder': 'Select Folder',
        'select_audio': 'Select Audio',
        'clear_audio': 'Reset',
        'work_list': '🎬 Work List',
        'run_merge': 'Run Merge',
        'menu_theme': 'Theme',
        'menu_light': 'Light Mode',
        'menu_dark': 'Dark Mode',
        'menu_language': 'Language',
        'lang_ko': 'Korean',
        'lang_en': 'English',
        'cpu_recommend': '[CPU Mode] {0}. 2x recommended.',
        'igpu_recommend': '[Intel QSV] {0}. 2x recommended, tile 200~400.',
        'gpu_recommend_high': 'GPU: {0} - 2x/4x, tile 400~600 recommended.',
        'gpu_recommend_mid': 'GPU: {0} - 2x, tile 200~300 recommended.',
        'gpu_recommend_low': 'GPU: {0} - 2x, tile 100~200 recommended.',
        'log_ffmpeg_start': "⏳ FFmpeg not found. Starting download...",
        'log_extracting': "📦 Extracting files...",
        'log_ffmpeg_error': "❌ FFmpeg installation error: {}",
        'log_ffmpeg_ready': "✅ FFmpeg Ready",
        'log_ffmpeg_fail': "❌ FFmpeg initial preparation failed",
        'log_downloading_model': "⏳ Downloading {}: ",
        'log_download_complete': "✅ Download Complete",
        'log_converting_model': "🔄 Converting to Intel GPU model (Scale x{})...",
        'log_convert_complete': "✅ Conversion Complete: {}",
        'log_convert_fail': "❌ Conversion Failed: {}",
        'log_upscale_complete': "✨ Upscale Completed",
        'log_error': "❌ Error: {}",
        'log_device_info': "🚀 Device: {}",
        'log_model_info': "📦 Model: {}",
        'log_res_optimized': "✅ Resolution Optimized: {}x{}",
        'log_parts_saved' : '📁 Part {} saved',
        'log_fatal_error': "🛑 Task stopped immediately due to hardware error.",
        'log_part_start': "🎬 Part {}/{} Start (Frame {}~{})",
        'log_merge_start': "🔄 Starting merge of all parts and audio synthesis...",
        'log_audio_source': "🔊 Audio source: {}",
        'log_audio_none': "🔊 No audio (Muted merge)",
        'log_merge_fail': "❌ Merge failed",
        'lang_name': "English",
        'log_lang_changed': "🌐 Language changed to: {}",
        'err_input_title': 'Input Error',
        'err_input_msg': 'Please select an input file.',
        'err_part_title': 'Input Error',
        'err_part_msg': 'Invalid target part format. (e.g., 0~9)',
        'log_files_found': '📁 Found {0} files in order.',
        'log_file_item': ' -> {0}',
        'warn_no_video_title': 'Warning',
        'warn_no_video_msg': 'No video files found in the folder.',
        'warn_no_folder_title': 'Warning',
        'warn_no_folder_msg': 'Please select a folder to merge first.',
        'save_dialog_title': 'Save Result',
        'save_dialog_filter': 'MP4 Files (*.mp4);;TS Files (*.ts)',
        'log_merge_success': '✅ Success: {0}',
        'log_merge_fail': '❌ Failed: {0}',
        'msg_merge_success_title': 'Success',
        'msg_merge_success_text': 'Video merge completed successfully.',
        'msg_merge_fail_title': 'Error',
        'msg_merge_fail_text': 'An error occurred during merge: {0}',
        'log_convert_success': '✅ Conversion completed: {0}',
        'log_convert_fail': '❌ Conversion failed: {0}',
        'log_unknown_opt_warn': 'Unknown optimization warning',
        'log_file_replace_fail': '❌ File replacement failed: {0}',
        'log_intel_convert': '🔄 Converting model for Intel GPU acceleration (Scale x{0})...',
        'log_download_complete': '✅ Download complete',
        'err_conn_title': 'Connection Error',
        'err_conn_text': 'Download Failed (Time-out)',
        'err_conn_info': 'Cannot download model due to network issues.\n\nError: {0}\n\nPlease restart the program.',
        'audio_select_title': 'Select Audio File',
        'audio_select_filter': 'Audio Files (*.mp3 *.wav *.aac *.m4a);;Video Files (*.mp4 *.mov *.avi *.mkv)',
        'log_audio_source': '🎵 Audio source set: {0}',
    }   
}

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