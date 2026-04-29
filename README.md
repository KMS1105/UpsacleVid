# Video Processing Project (None Finished)

이 프로젝트는 이미지/비디오 업스케일, 비디오 배경 제거를 지원하는 비디오 처리 애플리케이션입니다.

---

## 🛠 필요 라이브러리 설치
Intel/Nvidia 폴더 내의 requirements.txt

### Powershell

```bash
$env:PYTHONUTF8 = 1
pip install -r requirements.txt
```

### CMD

```bash
set PYTHONUTF8=1
pip install -r requirements.txt
```

---

## 🚀 실행

```bash
python Launch.py
```

---

## 🖥 주요 기능

### 🖼 이미지 업스케일

* Real-ESRGAN 기반 업스케일
* 모델 자동 다운로드
* [Intel] Intel GPU용 OpenVINO 자동 변환
* 2x, 4x

---

### 🎬 비디오 업스케일

* 비디오 **프레임 단위 분할 처리**
* 선택 파트 업스케일 지원 (예: `0~5`, `0,1,2`)
* 파트 별 업스케일 된 비디오 저장 (.ts)
* 멀티스레딩 파이프라인 처리
* OpenVINO 비동기 추론 지원
* FFmpeg 자동 인코딩
* GPU / CPU 모델 자동 전환

---

### 🎞 비디오 병합

* 중간 저장 된 (.ts)파일 병합
* 입력 오디오 선택 가능 (AAC)

---

### 🔽 모델 자동 다운로드

* 실행 시 필요한 Real-ESRGAN 모델 자동 다운로드

### ⚡[Intel] OpenVINO 자동 변환

* `.pth → .xml` 자동 변환
* Intel GPU 가속 최적화

### 🎥 FFmpeg 자동 설치

* FFmpeg 미설치 시 자동 다운로드 및 PATH 등록

---

## ⚡ 성능 가이드

| 환경        | 권장 설정                 |
| --------- | --------------------- |
| RTX       | 2x ~ 4x, tile 400~600 |
| GTX       | 2x, tile 200~300      |
| Intel GPU | 2x, tile 200~400      |
| CPU       | 2x, 분할 수 증가           |

---

## 🧩 기술 스택

* PyQt5 (GUI)
* Real-ESRGAN
* PyTorch
* OpenVINO
* OpenCV
* FFmpeg
* Multi-threading / Async Queue

---

## 📌 메모

* 최초 실행 시 모델 다운로드 및 변환으로 인해 시간이 소요될 수 있습니다.

---

## 🌐 English

### 🚀 Overview

This project is a desktop application based on **Real-ESRGAN** for enhancing image and video resolution.
It provides a PyQt5 GUI and supports **NVIDIA CUDA, Intel OpenVINO, and CPU auto-switching**.

It also includes **automatic model download, OpenVINO conversion, and FFmpeg setup**, allowing immediate use without manual configuration.

---

## 📂 Project Structure

```
📁 src/
 ├── weights/           # Auto-downloaded models and OpenVINO converted files
 ├── ffmpeg/            # FFmpeg auto-download
 └── 📁 Code/
      ├── Launch.py     # Main execution and UI
      ├── setting.py    # System detection / recommendations / theme
      ├── VideoMerge.py # Video merging feature
      ├── UpscaleImg.py # Image upscaling
      └── UpscaleVid.py # Video upscaling
requirements.txt
```

---

## 🛠 Required Library Installation

### Powershell

```bash
$env:PYTHONUTF8 = 1
pip install -r requirements.txt
```

### CMD

```bash
set PYTHONUTF8=1
pip install -r requirements.txt
```

### 🖥 Features

#### 🖼 Image Upscaling

* Real-ESRGAN based
* Automatic model download
* OpenVINO conversion for Intel GPU
* CUDA / OpenVINO / CPU auto selection
* Supports (2x / 4x)

#### 🎬 Video Upscaling

* Frame split processing
* Selective part upscale (`0~5`, `0,1,2`)
* Multi-threaded pipeline
* Async inference (OpenVINO)
* Automatic FFmpeg encoding

#### 🎞 Video Merging

* Drag-based timeline
* Clip reordering
* Automatic merge with audio

---

### ⚙ Automation

* Auto model download
* Auto OpenVINO conversion (.pth → .xml)
* Auto FFmpeg installation
* Hardware detection & optimization

---

### ⚡ Performance Guide

| Hardware  | Recommendation           |
| --------- | ------------------------ |
| RTX       | 2x–4x, tile 400–600      |
| GTX       | 2x, tile 200–300         |
| Intel GPU | 2x, tile 200–400         |
| CPU       | 2x, increase split count |

---

## 📝 License

Based on Real-ESRGAN
https://github.com/xinntao/Real-ESRGAN

---

## 📌 Notes

* On first run, model download and conversion may take some time.
* In CUDA environments, PyTorch reinstallation may be suggested automatically.
* FFmpeg will be downloaded and configured automatically.
