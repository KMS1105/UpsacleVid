import sys
import collections
import collections.abc

#Compatibility Patch
if not hasattr(collections, 'Iterable'):
    collections.Iterable = collections.abc.Iterable

try:
    import torchvision.transforms.functional as F
    
    sys.modules['torchvision.transforms.functional_tensor'] = F
    print("✅ torchvision 패치 성공")
except Exception as e:
    print(f"⚠️ 패치 중 알림: {e}")

import os
import cv2
import torch
from tqdm import tqdm

from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet

def run_split_upscale(input_path, num_splits, target_parts):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"🚀 실행 디바이스: {device}")
    
    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
    model_url = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth'
    
    upsampler = RealESRGANer(
        scale=2, 
        model_path=model_url, 
        model=model, 
        tile=800, 
        half=(device.type == 'cuda'), 
        device=device
    )

    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    frames_per_part = total_frames // num_splits
    parts_ranges = []
    for i in range(num_splits):
        start = i * frames_per_part
        end = (i + 1) * frames_per_part if i != num_splits - 1 else total_frames
        parts_ranges.append((start, end))

    print(f"📊 총 {total_frames} 프레임을 {num_splits}개 파트로 나눴습니다.")

    for part_idx in target_parts:
        if part_idx >= num_splits: continue
            
        start_f, end_f = parts_ranges[part_idx]
        output_path = f"./Vid/part_{part_idx}_upscaled.mov"
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_f)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width * 2, height * 2))

        print(f"🎬 Part {part_idx} 작업 중... ({start_f} ~ {end_f} frame)")
        
        try:
            for _ in tqdm(range(start_f, end_f), desc=f"Part {part_idx}"):
                ret, frame = cap.read()
                if not ret: break
                output, _ = upsampler.enhance(frame, outscale=2)
                out.write(output)
        finally:
            out.release()
            print(f"✅ Part {part_idx} 완료!")

    cap.release()

if __name__ == "__main__":
    input_file = './Vid/DamuiL79.mov'
    
    N = 10              
    WORK_LIST = [2]   

    if os.path.exists(input_file):
        run_split_upscale(input_file, N, WORK_LIST)
    else:
        print("❌ 원본 파일을 찾을 수 없습니다.")
