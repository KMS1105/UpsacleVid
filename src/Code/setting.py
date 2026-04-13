import platform
import subprocess
import psutil
import sys

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
                gpu = f"{h_gpu} (CUDA 미지원)" if h_gpu else (get_intel_gpu_name() or "CPU")
        except:
            h_gpu = get_hardware_gpu_name()
            gpu = f"{h_gpu} (라이브러리 오류)" if h_gpu else "Torch 미설치"
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
        'tab_video_merge': '영상 편집 (합치기)',
        'merge_video_list': '합칠 영상 목록 (드래그하여 순서 변경):',
        'add_video': '영상 추가',
        'remove_selected': '선택 삭제',
        'clear_all': '전체 삭제',
        'run_merge': '영상 합치기 실행',
        'error_min_videos': '최소 2개 이상의 영상을 추가해주세요.',
        'success_merge': '영상이 성공적으로 합쳐졌습니다!',
        'window_title': 'Upscaler - 영상/이미지 업스케일러',
        'tab_image': '이미지 업스케일',
        'tab_video': '비디오 업스케일',
        'menu_theme': '테마',
        'menu_light': '라이트 모드',
        'menu_dark': '다크 모드',
        'menu_language': '언어',
        'lang_ko': '한국어',
        'lang_en': '영어',
        'input_image': '입력 이미지:',
        'input_image_tip': '업스케일할 원본 이미지를 선택합니다.',
        'output_folder': '출력 폴더:',
        'output_folder_tip': '변환된 파일을 저장할 폴더를 선택합니다.',
        'scale': '배율:',
        'scale_tip': '2x, 4x, 8x 업스케일 배율을 선택합니다.',
        'input_video': '입력 비디오:',
        'input_video_tip': '업스케일할 원본 비디오 파일을 선택합니다.',
        'split_count': '분할 개수:',
        'split_count_tip': '비디오를 몇 개의 파트로 나눌지 지정합니다.',
        'target_parts': '대상 파트:',
        'target_parts_tip': "업스케일할 파트 범위를 입력하세요. (예: 0~5)\n시작 번호는 0이며, 쉼표로 여러 구간을 지정할 수 있습니다.\n\nEnter the part range to upscale. (e.g., 0~5)\nStarting index is 0. Multiple ranges can be separated by commas.",
        'tile_size': '타일 크기:',
        'tile_size_tip': 'Real-ESRGAN 블록 처리 크기입니다.\n0은 전체 프레임 처리, VRAM 부족 시 100~400 권장.',
        'browse': '찾아보기',
        'upscale_image': '이미지 업스케일 시작',
        'run_video_upscale': '비디오 업스케일 시작',
        'cpu_recommend': '[CPU 모드] {0} 사용 중. 속도가 매우 느릴 수 있습니다. 2x 권장 및 분할 개수를 최대한 높이세요.',
        'igpu_recommend': '[Intel QSV 가속] {0} 사용 중. 2x 권장, 타일 크기를 200~400으로 조절하세요.',
        'gpu_recommend_high': 'GPU: {0} - 권장: 2x/4x 사용, 고해상도 시 tile 400~600 권장.',
        'gpu_recommend_mid': 'GPU: {0} - 권장: 2x 사용, tile 200~300 권장.',
        'gpu_recommend_low': 'GPU: {0} - 권장: 2x 사용, tile 100~200 권장 (VRAM 주의).',
        'start_image': '▶ 이미지 작업을 시작합니다...',
        'start_video': '▶ 비디오 작업을 시작합니다...',
        'error_input_missing': '❌ 파일 없음: {0}',
        'error_output_folder': '❌ 폴더 없음: {0}',
        'error_no_output': '❌ 출력 폴더를 선택하세요.',
        'error_target_parts': '❌ 파트 번호는 숫자로 입력하세요.',
        'error_no_target_parts': '❌ 대상 파트를 지정하세요.',
        'video_timeline': '타임라인 (병합 순서)',
        'video_sources': '소스 미디어 리스트',
        'add': '가져오기',
        'add_to_timeline': '타임라인에 추가',
        'remove': '삭제',
        'clear': '비우기',
        'merge_quality': '화질 최적화 (자동 설정됨)',
        'export_video': '자동 최적화 내보내기 시작 (Intel QSV 가속)',
    },
    'en': {
        'tab_video_merge': 'Video Editor',
        'merge_video_list': 'Video List (Drag to reorder):',
        'add_video': 'Add Video',
        'remove_selected': 'Remove Selected',
        'clear_all': 'Clear All',
        'run_merge': 'Run Merge',
        'error_min_videos': 'Please add at least 2 videos.',
        'success_merge': 'Videos merged successfully!',
        'window_title': 'Upscaler',
        'tab_image': 'Image Upscale',
        'tab_video': 'Video Upscale',
        'menu_theme': 'Theme',
        'menu_light': 'Light Mode',
        'menu_dark': 'Dark Mode',
        'menu_language': 'Language',
        'lang_ko': 'Korean',
        'lang_en': 'English',
        'input_image': 'Input Image:',
        'input_image_tip': 'Select the source image.',
        'output_folder': 'Output Folder:',
        'output_folder_tip': 'Select save folder.',
        'scale': 'Scale:',
        'scale_tip': 'Select 2x, 4x, or 8x ratio.',
        'input_video': 'Input Video:',
        'input_video_tip': 'Select source video.',
        'split_count': 'Split Count:',
        'split_count_tip': 'Set video split parts.',
        'target_parts': 'Target Parts:',
        'target_parts_tip': "Enter the part range to upscale. (e.g., 0~5)\nStarting index is 0. Multiple ranges can be separated by commas.",
        'tile_size': 'Tile Size:',
        'tile_size_tip': '0 for whole frame, 100~400 recommended for stability.',
        'browse': 'Browse',
        'upscale_image': 'Start Image Upscale',
        'run_video_upscale': 'Start Video Upscale',
        'cpu_recommend': '[CPU Mode] Using {0}. Processing may be very slow. 2x recommended and increase split count.',
        'igpu_recommend': '[Intel QSV Acceleration] Using {0}. 2x recommended, adjust tile size to 200~400.',
        'gpu_recommend_high': 'GPU: {0} - Recommended: 2x/4x, tile 400~600.',
        'gpu_recommend_mid': 'GPU: {0} - Recommended: 2x, tile 200~300.',
        'gpu_recommend_low': 'GPU: {0} - Recommended: 2x, tile 100~200.',
        'start_image': '▶ Starting image task...',
        'start_video': '▶ Starting video task...',
        'error_input_missing': '❌ Missing file: {0}',
        'error_output_folder': '❌ Missing folder: {0}',
        'error_no_output': '❌ Select output folder.',
        'error_target_parts': '❌ Parts must be integers.',
        'error_no_target_parts': '❌ Enter target part.',
        'video_timeline': 'Timeline (Merge Order)',
        'video_sources': 'Source Media List',
        'add': 'Import',
        'add_to_timeline': 'Add to Timeline',
        'remove': 'Remove',
        'clear': 'Clear',
        'merge_quality': 'Quality Optimized (Auto)',
        'export_video': 'Start Optimized Export (Intel QSV Accel)',
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
        """
    else:
        style = """
            QMainWindow { background-color: #f5f5f7; }
            QWidget { background-color: #ffffff; color: #202124; font-family: 'Malgun Gothic', sans-serif; font-size: 13px; }
            QToolTip { background-color: #ffffff; color: #202124; border: 1px solid #dadce0; border-radius: 4px; padding: 8px; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox { background-color: #ffffff; color: #202124; border: 1px solid #dadce0; border-radius: 6px; padding: 5px; }
            QPushButton { background-color: #1a73e8; color: #ffffff; border: none; border-radius: 6px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #185abc; }
            QProgressBar { background-color: #e8eaed; border: 1px solid #dadce0; border-radius: 8px; text-align: center; color: #3c4043; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a73e8, stop:1 #4285f4); border-radius: 7px; }
            QTabWidget::pane { border: 1px solid #dadce0; background-color: #ffffff; top: -1px; }
            QTabBar::tab { background-color: #f1f3f4; color: #5f6368; padding: 12px 25px; border: 1px solid #dadce0; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; }
            QTabBar::tab:selected { background-color: #ffffff; color: #1a73e8; border-bottom: 3px solid #1a73e8; font-weight: bold; }
            QListWidget, QListView, QScrollArea, QAbstractScrollArea { background-color: #ffffff !important; color: #202124 !important; border: 1px solid #dadce0; }
            QListWidget::item { background-color: #ffffff; color: #202124; }
            QListWidget::item:selected { background-color: #e8f0fe; color: #1a73e8; }
            QLabel { background-color: transparent !important; color: #202124 !important; }
            QGroupBox { border: 1px solid #dadce0; border-radius: 8px; margin-top: 10px; padding-top: 10px; background-color: #ffffff; }
        """
    widget.setStyleSheet(style)