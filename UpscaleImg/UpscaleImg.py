import sys
import collections
import collections.abc

if not hasattr(collections, 'Iterable'):
    collections.Iterable = collections.abc.Iterable

try:
    import torchvision.transforms.functional as F
    sys.modules['torchvision.transforms.functional_tensor'] = F
except ImportError:
    pass

import os
import cv2
import torch
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet

def upscale_single_image(input_path, output_path):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"🚀 실행 디바이스: {device}")

    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
    model_url = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth'

    upsampler = RealESRGANer(
        scale=2,
        model_path=model_url,
        model=model,
        tile=0, 
        tile_pad=10,
        pre_pad=0,
        half=True if device.type == 'cuda' else False,
        device=device
    )

    img = cv2.imread(input_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"❌ 이미지를 찾을 수 없습니다: {input_path}")
        return

    try:
        print(f"✅ 업스케일링 시작... (원본 크기: {img.shape[1]}x{img.shape[0]})")
        output, _ = upsampler.enhance(img, outscale=2)
        
        cv2.imwrite(output_path, output)
        print(f"✨ 완료! 결과가 저장되었습니다: {os.path.abspath(output_path)}")
    except Exception as e:
        print(f"❌ 처리 중 에러 발생: {e}")

if __name__ == "__main__":
    input_img_name = './Img/DanuiL79T.png' 
    output_img_name = './Img/input_2x.png'

    if os.path.exists(input_img_name):
        upscale_single_image(input_img_name, output_img_name)
    else:
        print(f"❌ '{input_img_name}' 파일이 폴더에 없습니다.")
