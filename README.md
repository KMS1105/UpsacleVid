# 🚀 AI Upscaler Project

이 프로젝트는 **Real-ESRGAN** 알고리즘을 기반으로 이미지와 비디오의 화질을 개선하는 데스크톱 애플리케이션입니다. 사용자 친화적인 GUI를 통해 누구나 쉽게 고해상도 변환 작업을 수행할 수 있습니다.

---

## 📂 1. 프로젝트 구성 (Project Structure)

본 프로그램은 총 4개의 파이썬 파일로 구성되어 있습니다. 모든 파일은 동일한 폴더에 위치해야 합니다.

* **Launch.py**: 프로그램의 메인 실행 파일입니다. 전체 GUI 인터페이스와 탭 구성을 관리합니다.
* **setting.py**: 다크/라이트 테마 디자인(CSS), 하드웨어(GPU/CPU) 감지 로직이 포함되어 있습니다.
* **UpscaleImg.py**: 이미지 업스케일링을 담당하는 전용 모듈입니다.
* **UpscaleVid.py**: 비디오를 파트별로 분할하여 업스케일링하는 전용 모듈입니다.

---

## 🛠 2. 설치 방법 (Installation)

프로그램 실행을 위해 필요한 라이브러리를 터미널(CMD)에서 설치해야 합니다.

    # 필수 라이브러리 설치
    pip install PyQt5 torch torchvision opencv-python basicsr realesrgan

> 참고: NVIDIA 그래픽카드를 사용 중이라면 CUDA Toolkit을 설치하여 하드웨어 가속을 사용할 수 있습니다.

---

## 🚀 3. 실행 방법 (Execution)

터미널 또는 명령 프롬프트에서 프로젝트 폴더로 이동한 뒤 아래 명령어를 입력합니다.

    python Launch.py

---

## 🖥 4. 사용 방법 (Manual)

### 🖼 이미지 업스케일 (Image Tab)

* **입력 이미지**: '찾아보기' 버튼을 눌러 원본 사진을 선택합니다.
* **출력 폴더**: 결과물이 저장될 폴더를 지정합니다.
* **배율 설정**: 2x, 4x, 8x 중 원하는 업스케일 크기를 선택합니다.
* **실행**: '이미지 업스케일' 버튼을 클릭합니다.

---

### 🎬 비디오 업스케일 (Video Tab)

* **분할 개수**: 긴 영상을 여러 개로 나눌 개수를 설정합니다. (사양이 낮을수록 높게 설정 권장)
* **대상 파트**: 업스케일링을 수행할 파트 번호를 입력합니다. (예: 0 또는 0,1,2)
* **타일 크기 (Tile Size)**: VRAM 용량이 부족하다면 100~400 사이의 값을 입력합니다. (0은 전체 처리)
* **실행**: '비디오 업스케일 실행' 버튼을 클릭합니다.

---

## 💡 주요 기능 및 팁

* **테마 변경**: 상단 메뉴 [테마]에서 '라이트' 또는 '다크' 모드를 즉시 전환할 수 있습니다.
* **언어 설정**: [언어] 메뉴를 통해 '한국어'와 'English' 중 선택이 가능합니다.
* **장치 추천**: 프로그램 하단에 현재 PC 사양에 맞는 최적의 설정 값이 자동으로 표시됩니다.
* **에러 방지**: 이미지/비디오 경로에 한글이 포함되어 있어도 정상 작동하도록 설계되었습니다.

---

## 📝 라이선스 (License)

본 프로그램은 오픈소스 알고리즘인 Real-ESRGAN을 활용합니다.

* 알고리즘 상세 정보: https://github.com/xinntao/Real-ESRGAN

---

# 🚀 AI Upscaler Project

This project is a desktop application based on the Real-ESRGAN algorithm, designed to enhance the quality of images and videos. With a user-friendly GUI, anyone can easily perform high-resolution upscaling.

---

## 📂 1. Project Structure

This program consists of 4 Python files. All files must be located in the same folder.

* **Launch.py**: Main entry point of the program. Manages the GUI interface and tab structure.
* **setting.py**: Contains theme (dark/light) design and hardware detection logic (GPU/CPU).
* **UpscaleImg.py**: Dedicated module for image upscaling.
* **UpscaleVid.py**: Dedicated module that splits videos into parts and upscales them.

---

## 🛠 2. Installation

To run the program, install the required libraries via terminal (CMD):

    # Install required libraries
    pip install PyQt5 torch torchvision opencv-python basicsr realesrgan

> Note: If you are using an NVIDIA GPU, install CUDA Toolkit to enable hardware acceleration.

---

## 🚀 3. Execution

Navigate to the project folder in your terminal or command prompt and run:

    python Launch.py

---

## 🖥 4. Manual

### 🖼 Image Upscale (Image Tab)

* **Input Image**: Click “Browse” to select the original image.
* **Output Folder**: Select the folder where results will be saved.
* **Scale Factor**: Choose 2x, 4x, or 8x.
* **Run**: Click “Upscale Image”.

---

### 🎬 Video Upscale (Video Tab)

* **Split Count**: Number of segments to divide the video into (Higher values recommended for low-spec PCs)
* **Target Parts**: Enter part indices to process (e.g., 0 or 0,1,2)
* **Tile Size**: If VRAM is limited, use 100–400 (0 = full processing)
* **Run**: Click “Start Video Upscaling”.

---

## 💡 Features & Tips

* **Theme Switching**: Toggle Light/Dark mode from the top menu
* **Language**: Supports Korean and English
* **Device Recommendation**: Automatically suggests optimal settings
* **Error Prevention**: Works with Korean file paths

---

## 📝 License

This program uses the open-source algorithm Real-ESRGAN.

* More info: https://github.com/xinntao/Real-ESRGAN
