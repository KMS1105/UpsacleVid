# 🚀 AI Upscaler Project

이 프로젝트는 **Real-ESRGAN** 알고리즘을 기반으로 이미지와 비디오의 화질을 개선하는 데스크톱 애플리케이션입니다. 사용자 친화적인 GUI를 통해 누구나 쉽게 고해상도 변환 작업을 수행할 수 있습니다. 특히 **NVIDIA(CUDA)** 뿐만 아니라 **Intel(OpenVINO)** 하드웨어 가속을 지원하여 다양한 PC 환경에서 최적의 성능을 발휘합니다.

---

## 📂 1. 프로젝트 구성 (Project Structure)

본 프로그램은 총 4개의 파이썬 파일로 구성되어 있습니다. 모든 파일은 동일한 폴더에 위치해야 합니다.

* **Launch.py**: 프로그램의 메인 실행 파일입니다. 전체 GUI 인터페이스와 탭 구성을 관리합니다.
* **setting.py**: 다크/라이트 테마 디자인, 하드웨어(NVIDIA/Intel/CPU) 감지 및 가속 로직이 포함되어 있습니다.
* **UpscaleImg.py**: 이미지 업스케일링을 담당하는 전용 모듈입니다.
* **UpscaleVid.py**: 비디오를 파트별로 분할하여 업스케일링하는 전용 모듈입니다.

---

## 🛠 2. 설치 방법 (Installation)

의존성 충돌을 방지하기 위해 제공된 `requirements.txt`를 사용하여 라이브러리를 설치해야 합니다. 터미널(CMD)에서 아래 명령어를 입력하세요.

```bash
# 필수 라이브러리 일괄 설치
pip install -r requirements.txt
```

### 참고:

* **NVIDIA 사용자**: CUDA Toolkit을 설치하면 더욱 빠른 가속이 가능합니다.
* **Intel 사용자**: 별도의 복잡한 설정 없이 내장/외장(Arc) 그래픽 가속이 자동으로 활성화됩니다.

---

## 🚀 3. 실행 방법 (Execution)

터미널 또는 명령 프롬프트에서 프로젝트 폴더로 이동한 뒤 아래 명령어를 입력합니다.

```bash
python Launch.py
```

---

## 🖥 4. 사용 방법 (Manual)

### 🖼 이미지 업스케일 (Image Tab)

* **입력 이미지**: '찾아보기' 버튼을 눌러 원본 사진을 선택합니다.
* **출력 폴더**: 결과물이 저장될 폴더를 지정합니다.
* **배율 설정**: 2x, 4x, 8x 중 원하는 업스케일 크기를 선택합니다.
* **실행**: '이미지 업스케일 시작' 버튼을 클릭합니다.

### 🎬 비디오 업스케일 (Video Tab)

* **분할 개수**: 긴 영상을 여러 개로 나눌 개수를 설정합니다. (사양이 낮을수록 높게 설정 권장)
* **대상 파트**: 업스케일링을 수행할 파트 번호를 입력합니다. (예: 0 또는 0,1,2)
* **타일 크기 (Tile Size)**: VRAM이나 시스템 메모리가 부족하다면 100~400 사이의 값을 입력합니다. (0은 전체 프레임 처리)
* **실행**: '비디오 업스케일 시작' 버튼을 클릭합니다.

---

## 💡 주요 기능 및 팁

* **하드웨어 가속**: NVIDIA GPU가 없어도 Intel OpenVINO 기술을 통해 인텔 그래픽 카드에서 가속이 지원됩니다.
* **테마/언어**: 상단 메뉴를 통해 다크 모드 전환 및 한국어/영어 설정을 즉시 변경할 수 있습니다.
* **장치 추천**: 프로그램 하단에 현재 PC 사양에 맞는 최적의 타일(Tile) 크기와 권장 설정이 자동으로 표시됩니다.

---

## 📝 라이선스 (License)

본 프로그램은 오픈소스 알고리즘인 Real-ESRGAN을 활용합니다.

* 알고리즘 상세 정보: [https://github.com/xinntao/Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN)

---

# 🚀 AI Upscaler Project (English)

This project is a desktop application based on the Real-ESRGAN algorithm, designed to enhance the quality of images and videos. It supports both NVIDIA (CUDA) and Intel (OpenVINO) hardware acceleration, ensuring optimal performance across various PC environments.

---

## 📂 1. Project Structure

* **Launch.py**: Main entry point. Manages the GUI and tab structure.
* **setting.py**: Contains theme (dark/light) design and hardware detection (NVIDIA/Intel/CPU).
* **UpscaleImg.py**: Dedicated module for image upscaling.
* **UpscaleVid.py**: Dedicated module for video segment upscaling.

---

## 🛠 2. Installation

```bash
# Install all required libraries
pip install -r requirements.txt
```

---

## 🚀 3. Execution

```bash
python Launch.py
```

---

## 🖥 4. Manual

### 🖼 Image Upscale

* Input/Output: Select the source image and destination folder.
* Scale Factor: Choose 2x, 4x, or 8x.
* Run: Click “Start Image Upscale”.

### 🎬 Video Upscale

* Split Count: Number of segments to divide the video into.
* Target Parts: Enter part indices (e.g., 0 or 0,1,2).
* Tile Size: Use 100–400 for low VRAM/Memory (0 = full processing).
* Run: Click “Start Video Upscale”.

---

## 💡 Features & Tips

* Hardware Acceleration: Automatically detects and uses NVIDIA GPUs or Intel Graphics (via OpenVINO) for faster processing.
* UI Customization: Supports Dark/Light mode and Korean/English language switching.
* Dynamic Recommendations: Provides optimal settings based on your current hardware specs.
