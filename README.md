# Video Processing Project (Not Finished)


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

---

### 🎞 비디오 병합

* 중간 저장 된 (.ts)파일 병합
* 입력 오디오 선택 가능 (AAC)

---

### [Intel] 배경 제거
* **Modnet**을 통해 (객체, 배경) 감지, 제거
* **Bisenet**을 통해 얼굴 감지
* **mod_fp16** 경계선 보정

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

## 📌 주의사항

* 최초 실행 시 모델 다운로드 및 변환으로 인해 시간이 소요될 수 있습니다.

---
