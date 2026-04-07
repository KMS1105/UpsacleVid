import platform
import torch
import subprocess

def get_intel_gpu_name():
    try:
        if platform.system() == "Windows":
            cmd = "wmic path win32_VideoController get name"
            output = subprocess.check_output(cmd, shell=True).decode('utf-8')
            gpu_list = [line.strip() for line in output.split('\n') if "Intel" in line.strip()]
            
            if not gpu_list: return None
            
            # 우선순위: Arc(외장) -> Iris(고성능 내장) -> UHD/기타(일반 내장)
            for keyword in ["Arc", "Iris", "Intel"]:
                for gpu in gpu_list:
                    if keyword in gpu:
                        return gpu
    except:
        pass
    return None

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
        'target_parts_tip': '업스케일할 파트 번호를 쉼표로 구분하여 입력합니다.\n시작 파트 번호는 0입니다.',
        'tile_size': '타일 크기:',
        'tile_size_tip': 'Real-ESRGAN 블록 처리 크기입니다.\n0은 전체 프레임 처리, VRAM 부족 시 100~400 권장.',
        'browse': '찾아보기',
        'upscale_image': '이미지 업스케일 시작',
        'run_video_upscale': '비디오 업스케일 시작',
        'device_label': '장치: ',
        'cpu_recommend': '장치: {0}\n[Intel QSV 가속 활성] 2x 권장, 분할 개수를 높여 처리하세요.',
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
        'timeline_preview_msg': '영상을 추가하여 시퀀스를 구성하세요.',
        'video_sources': '소스 미디어 리스트',
        'add': '가져오기',
        'remove': '삭제',
        'clear': '비우기',
        'merge_quality': '내보내기 화질 (Intel QSV 가속 적용)',
        'export_video': '최종 영상 내보내기',
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
        'target_parts_tip': 'Enter part numbers separated by commas.',
        'tile_size': 'Tile Size:',
        'tile_size_tip': '0 for whole frame, 100~400 recommended for stability.',
        'browse': 'Browse',
        'upscale_image': 'Start Image Upscale',
        'run_video_upscale': 'Start Video Upscale',
        'device_label': 'Device: ',
        'cpu_recommend': 'Device: {0}\n[Intel QSV Accel On] Use 2x, increase split count.',
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
        'timeline_preview_msg': 'Add videos to build sequence.',
        'video_sources': 'Source Media List',
        'add': 'Add',
        'remove': 'Remove',
        'clear': 'Clear',
        'merge_quality': 'Export Quality (Intel QSV Accel On)',
        'export_video': 'Export Video',
    }
}

def get_device_info_text(lang='ko'):
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
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        lower_name = gpu_name.lower()
        if any(kw in lower_name for kw in ['rtx', 'a100', 'v100', 'titan', 'h100']):
            return texts['gpu_recommend_high'].format(gpu_name)
        if any(kw in lower_name for kw in ['gtx', '1660', '1080', '1070']):
            return texts['gpu_recommend_mid'].format(gpu_name)
        return texts['gpu_recommend_low'].format(gpu_name)
    
    intel_gpu = get_intel_gpu_name()
    display_name = intel_gpu if intel_gpu else platform.processor() or 'Unknown CPU'
    return texts['cpu_recommend'].format(display_name)

def apply_app_theme(widget, theme):
    if theme == 'dark':
        widget.setStyleSheet("""
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
        """)
    else:
        widget.setStyleSheet("""
            QMainWindow { background-color: #f0f2f5; }
            QWidget { background-color: #ffffff; color: #202124; font-family: 'Malgun Gothic', sans-serif; font-size: 13px; }
            QToolTip { background-color: #202124; color: #ffffff; border: 1px solid #202124; border-radius: 4px; padding: 8px; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox { background-color: #f8f9fa; color: #202124; border: 1px solid #dadce0; border-radius: 6px; padding: 5px; }
            QPushButton { background-color: #1a73e8; color: #ffffff; border: none; border-radius: 6px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #185abc; }
            QProgressBar { background-color: #e8eaed; border: 1px solid #dadce0; border-radius: 8px; text-align: center; color: #3c4043; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a73e8, stop:1 #4285f4); border-radius: 7px; }
            QTabWidget::pane { border: 1px solid #dadce0; background-color: #ffffff; top: -1px; }
            QTabBar::tab { background-color: #f1f3f4; color: #5f6368; padding: 12px 25px; border: 1px solid #dadce0; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; }
            QTabBar::tab:selected { background-color: #ffffff; color: #1a73e8; border-bottom: 3px solid #1a73e8; font-weight: bold; }
        """)