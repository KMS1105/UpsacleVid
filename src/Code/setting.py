import platform
import torch

UI_TEXTS = {
    'ko': {
        'window_title': 'Upscaler',
        'tab_image': '이미지',
        'tab_video': '비디오',
        'menu_theme': '테마',
        'menu_light': '라이트',
        'menu_dark': '다크',
        'menu_language': '언어',
        'lang_ko': '한국어',
        'lang_en': 'English',
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
        'tile_size_tip': 'Tile Size <- Real-ESRGAN이 입력을 여러 블록으로 나누어 처리하는 크기입니다.\n0은 전체 프레임을 한 번에 처리하며, VRAM 부족 시 100~400 설정을 권장합니다.',
        'browse': '찾아보기',
        'upscale_image': '이미지 업스케일',
        'run_video_upscale': '비디오 업스케일 실행',
        'device_label': 'Device: ',
        'cpu_recommend': 'CPU: {0} - 권장: 2x 사용, 비디오 split count를 높여 처리하세요.',
        'gpu_recommend_high': 'GPU: {0} - 권장: 2x/4x 사용, 고해상도 시 tile 400~600 권장.',
        'gpu_recommend_mid': 'GPU: {0} - 권장: 2x 사용, tile 200~300 권장 (4x는 매우 느림).',
        'gpu_recommend_low': 'GPU: {0} - 권장: 2x 사용, tile 100~200 권장 (VRAM 부족 주의).',
        'start_image': '▶ 이미지 업스케일 작업을 시작합니다...',
        'start_video': '▶ 비디오 업스케일 작업을 시작합니다...',
        'error_input_missing': '❌ 입력 파일이 존재하지 않습니다: {0}',
        'error_output_folder': '❌ 출력 폴더가 존재하지 않습니다: {0}',
        'error_no_output': '❌ 출력 폴더를 선택하세요.',
        'error_target_parts': '❌ Target Parts는 쉼표로 구분된 정수여야 합니다.',
        'error_no_target_parts': '❌ 최소 하나의 Target Part를 지정하세요.',
    },
    'en': {
        'window_title': 'Upscaler',
        'tab_image': 'Image',
        'tab_video': 'Video',
        'menu_theme': 'Theme',
        'menu_light': 'Light',
        'menu_dark': 'Dark',
        'menu_language': 'Language',
        'lang_ko': '한국어',
        'lang_en': 'English',
        'input_image': 'Input Image:',
        'input_image_tip': 'Select the source image to upscale.',
        'output_folder': 'Output Folder:',
        'output_folder_tip': 'Choose the folder to save the converted file.',
        'scale': 'Scale:',
        'scale_tip': 'Select the upscaling ratio: 2x, 4x, or 8x.',
        'input_video': 'Input Video:',
        'input_video_tip': 'Select the source video file to upscale.',
        'split_count': 'Split Count:',
        'split_count_tip': 'Set how many parts the video will be split into.',
        'target_parts': 'Target Parts:',
        'target_parts_tip': 'Enter part numbers to upscale, separated by commas.',
        'tile_size': 'Tile Size:',
        'tile_size_tip': 'Tile Size <- Real-ESRGAN divides the input into blocks.\n0 processes the whole frame at once; 100~400 is recommended for stability.',
        'browse': 'Browse',
        'upscale_image': 'Upscale Image',
        'run_video_upscale': 'Run Video Upscale',
        'device_label': 'Device: ',
        'cpu_recommend': 'CPU: {0} - Recommended: use 2x, increase split count for video processing.',
        'gpu_recommend_high': 'GPU: {0} - Recommended: 2x/4x, tile 400~600 for stable upscaling.',
        'gpu_recommend_mid': 'GPU: {0} - Recommended: 2x, tile 200~300 (4x takes significant time).',
        'gpu_recommend_low': 'GPU: {0} - Recommended: 2x, tile 100~200 (Risk of VRAM OOM errors).',
        'start_image': '▶ Starting image upscale task...',
        'start_video': '▶ Starting video upscale task...',
        'error_input_missing': '❌ Input file does not exist: {0}',
        'error_output_folder': '❌ Output folder does not exist: {0}',
        'error_no_output': '❌ Please select an output folder.',
        'error_target_parts': '❌ Target Parts must be comma-separated integers.',
        'error_no_target_parts': '❌ Please enter at least one target part.',
    }
}

def get_device_info_text(lang='ko'):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if device.type == 'cuda':
        gpu_name = torch.cuda.get_device_name(0)
        return f"{UI_TEXTS[lang]['device_label']}GPU ({gpu_name})"
    cpu_name = platform.processor() or 'Unknown CPU'
    return f"{UI_TEXTS[lang]['device_label']}CPU ({cpu_name})"

def get_device_recommendation(lang='ko'):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    texts = UI_TEXTS[lang]
    if device.type == 'cuda':
        gpu_name = torch.cuda.get_device_name(0)
        lower_name = gpu_name.lower()
        if any(kw in lower_name for kw in ['rtx', 'a100', 'v100', 'titan', 'h100']):
            return texts['gpu_recommend_high'].format(gpu_name)
        if any(kw in lower_name for kw in ['gtx', '1660', '1080', '1070']):
            return texts['gpu_recommend_mid'].format(gpu_name)
        return texts['gpu_recommend_low'].format(gpu_name)
    cpu_name = platform.processor() or 'Unknown CPU'
    return texts['cpu_recommend'].format(cpu_name)

def apply_app_theme(widget, theme):
    if theme == 'dark':
        widget.setStyleSheet("""
            QMainWindow { background-color: #121212; }
            QWidget { background-color: #1e1e1e; color: #e0e0e0; font-family: 'Malgun Gothic', sans-serif; font-size: 13px; }
            QToolTip { background-color: #333333; color: #ffffff; border: 1px solid #00bcff; border-radius: 4px; padding: 5px; }
            QLineEdit, QTextEdit, QComboBox, QSpinBox { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3e3e42; border-radius: 4px; padding: 5px; }
            QPushButton { background-color: #3a3a3a; color: #ffffff; border: 1px solid #505050; border-radius: 5px; padding: 8px 15px; font-weight: bold; }
            QPushButton:hover { background-color: #4a4a4a; border: 1px solid #007acc; }
            QPushButton[class="help-button"] { color: #00bcff; background-color: #2d2d2d; border: 1px solid #00bcff; border-radius: 10px; font-weight: bold; }
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
            QPushButton[class="help-button"] { color: #ffffff; background-color: #1a73e8; border: none; border-radius: 10px; font-weight: bold; }
            QProgressBar { background-color: #e8eaed; border: 1px solid #dadce0; border-radius: 8px; text-align: center; color: #3c4043; }
            QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1a73e8, stop:1 #4285f4); border-radius: 7px; }
            QTabWidget::pane { border: 1px solid #dadce0; background-color: #ffffff; top: -1px; }
            QTabBar::tab { background-color: #f1f3f4; color: #5f6368; padding: 12px 25px; border: 1px solid #dadce0; border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 4px; }
            QTabBar::tab:selected { background-color: #ffffff; color: #1a73e8; border-bottom: 3px solid #1a73e8; font-weight: bold; }
        """)