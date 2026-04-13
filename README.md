# 🚀 AI Upscaler Project Beta

이 프로젝트는 **Real-ESRGAN** 기반으로 이미지 및 비디오의 해상도를 향상시키는 데스크톱 애플리케이션입니다.  
PyQt5 기반 GUI와 **NVIDIA CUDA / Intel OpenVINO / CPU 자동 전환 시스템**을 통해 다양한 환경에서 최적의 성능을 제공합니다.

---

### 📂 프로젝트 구성

```
📁 src/
 ├── weights/ (자동 다운로드)
 ├── ffmpeg/ (자동 다운로드)
 └── 📁 Code/
      ├── Launch.py
      ├── setting.py
      ├── VideoMerge.py
      ├── UpscaleImg.py
      └── UpscaleVid.py
requirements.txt
```

---

### 🛠 설치

#### Powershell

```bash
$env:PYTHONUTF8 = 1
pip install -r requirements.txt
```

#### CMD

```bash
set PYTHONUTF8=1
pip install -r requirements.txtt
```

---

### 🚀 실행

```bash
python Launch.py
```

---

### 🖥 주요 기능

#### 🖼 이미지 업스케일
- Real-ESRGAN 기반
- 2x / 4x / 8x 지원
- GPU / CPU 자동 선택

#### 🎬 비디오 업스케일
- 분할 처리
- 멀티스레딩 처리
- FFmpeg 자동 인코딩

#### 🎞 비디오 병합
- 드래그 타임라인
- 영상 순서 변경
- 자동 병합

---

### ⚡ 성능 가이드

- RTX: 4x 권장
- GTX: 2x 권장
- Intel GPU: 2x 권장
- CPU: 느림 (분할 개수 증가)

---

This project is a desktop application based on **Real-ESRGAN** for enhancing image and video resolution.  
It uses a PyQt5 GUI and supports **NVIDIA CUDA, Intel OpenVINO, and CPU auto-switching** for optimal performance across systems.

---

### 📂 Project Structure

```
📁 src/
 ├── weights/ (auto download)
 ├── ffmpeg/ (auto download)
 └── 📁 Code/
      ├── Launch.py
      ├── setting.py
      ├── VideoMerge.py
      ├── UpscaleImg.py
      └── UpscaleVid.py
requirements.txt
```

---

### 🛠 Installation

```bash
pip install -r requirements.txt
```

---

### 🚀 Run

```bash
python Launch.py
```

---

### 🖥 Features

#### 🖼 Image Upscaling
- Real-ESRGAN based
- Supports 2x / 4x / 8x
- Auto GPU / CPU selection

#### 🎬 Video Upscaling
- Split processing
- Multi-threaded pipeline
- FFmpeg encoding

#### 🎞 Video Merging
- Drag-based timeline
- Reorder clips
- Automatic merging

---

### ⚡ Performance Guide

- RTX: Recommended 4x
- GTX: Recommended 2x
- Intel GPU: Recommended 2x
- CPU: Slow (increase split count)

---

## 📝 License

Based on Real-ESRGAN  
https://github.com/xinntao/Real-ESRGAN
