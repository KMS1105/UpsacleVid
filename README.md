# 🚀 AI Upscaler Project Beta

이 프로젝트는 **Real-ESRGAN** 기반으로 이미지 및 비디오의 해상도를 향상시키는 데스크톱 애플리케이션입니다.
PyQt5 GUI와 **NVIDIA CUDA / Intel OpenVINO / CPU 자동 전환 시스템**을 통해 다양한 환경에서 최적의 성능을 제공합니다.

또한, 모델 자동 다운로드 / OpenVINO 변환 / FFmpeg 자동 설치 기능을 포함하여 **초기 설정 없이 바로 사용 가능**하도록 설계되었습니다.

---

## 📂 프로젝트 구성

```
📁 src/
 ├── weights/           # 모델 자동 다운로드 및 OpenVINO 변환 결과
 ├── ffmpeg/            # FFmpeg 자동 다운로드
 └── 📁 Code/
      ├── Launch.py     # 메인 실행 및 UI
      ├── setting.py    # 시스템 감지 / 추천 설정 / 테마
      ├── VideoMerge.py # 영상 병합 기능
      ├── UpscaleImg.py # 이미지 업스케일
      └── UpscaleVid.py # 비디오 업스케일
requirements.txt
```

---

## 🛠 설치

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
* Intel GPU용 OpenVINO 자동 변환
* CUDA / OpenVINO / CPU 자동 선택
* 다양한 모델 (2x / 4x)

---

### 🎬 비디오 업스케일

* 비디오 **프레임 단위 분할 처리**
* 선택 파트 업스케일 지원 (예: `0~5`, `0,1,2`)
* 멀티스레딩 파이프라인 처리
* OpenVINO 비동기 추론 지원
* FFmpeg 자동 인코딩
* GPU / CPU 모델 자동 전환

---

### 🎞 비디오 병합

* 드래그 기반 타임라인
* 영상 순서 변경 가능
* 여러 파일 자동 병합
* 오디오 유지 병합 (AAC)

---

## ⚙ 자동화 기능

### 🔽 모델 자동 다운로드

* 실행 시 필요한 Real-ESRGAN 모델 자동 다운로드

### ⚡ OpenVINO 자동 변환

* CUDA 미사용 환경에서 `.pth → .xml` 자동 변환
* Intel GPU 가속 최적화

### 🎥 FFmpeg 자동 설치

* FFmpeg 미설치 시 자동 다운로드 및 PATH 등록

### 🧠 하드웨어 자동 감지

* GPU / CPU 상태 분석
* 환경에 맞는 설정 자동 추천

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

## 🌐 English

### 🚀 Overview

This project is a desktop application based on **Real-ESRGAN** for enhancing image and video resolution.
It provides a PyQt5 GUI and supports **NVIDIA CUDA, Intel OpenVINO, and CPU auto-switching**.

It also includes **automatic model download, OpenVINO conversion, and FFmpeg setup**, allowing immediate use without manual configuration.

---

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

* 최초 실행 시 모델 다운로드 및 변환으로 인해 시간이 소요될 수 있습니다.
* CUDA 환경에서는 PyTorch 재설치가 자동으로 제안될 수 있습니다.
* FFmpeg는 자동으로 다운로드 및 설정됩니다.
