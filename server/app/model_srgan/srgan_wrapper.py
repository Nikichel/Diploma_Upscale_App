import numpy as np
import torch
from model_srgan.generator import Generator
from transform.transform import Transforms
import io
from PIL import Image
import base64
from typing import Optional
from utils.server_logger import ServerLogger
import os
import cv2

from fastapi import HTTPException, status

class SRGANWrapper:
    def __init__(self):
        """Инициализация обертки для модели SRGAN"""
        self.logger = ServerLogger()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = Generator(in_channels=3).to(self.device)
        self.transform = Transforms()
        self.ready = False
        self.logger.info(f"Initialized SRGAN wrapper on device: {self.device}")
    
    async def load_model(self) -> bool:
        """Загрузка модели SRGAN"""
        try:
            # Для асинхронной загрузки модели используем executor
            checkpoint = torch.load(os.getenv("PATH_TO_MODEL"),map_location=self.device) # тут загрузка generatora
            self.model.load_state_dict(checkpoint["generator_state_dict"])
            
            self.model.eval()
            self.ready = True
            # return True
        except Exception as e:
            print(f"Ошибка при загрузке модели SRGAN: {e}")
            self.ready = False
            # return False
    
    async def upscale_image(self, image_data: bytes, scale_factor: int = 4, use_decoration: bool = False) -> Optional[str]:
        """Увеличение разрешения изображения с помощью SRGAN"""
        max_shape = int(os.getenv("MAX_SHAPE", 1000))

        if not self.ready or self.model is None:
            self.logger.error("Model not loaded")
            raise RuntimeError("Модель SRGAN не загружена")

        try:
            self.logger.log_image_processing(len(image_data), None)
            
            if len(image_data) == 0:
                raise ValueError("Получены пустые данные изображения")
            
            image_bytes = io.BytesIO(image_data)
            image_bytes.seek(0)
            
            try:
                img = Image.open(image_bytes)
                img = img.convert('RGB')
                self.logger.debug(f"Image opened: format={img.format}, mode={img.mode}")
            except Exception as img_error:
                self.logger.log_error(img_error, "image_opening")
                raise
            
            img_array = np.array(img)
            self.logger.debug(f"Image converted to array: shape={img_array.shape}")
            
            if img_array.shape[0] > max_shape or img_array.shape[1] > max_shape:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Изображение превышает {max_shape}x{max_shape} пикселей"
                )        

            SR_image = await self.upscale_x4(use_decoration, img_array)

            if scale_factor == 2 or scale_factor == 8:
                SR_image = cv2.resize(SR_image, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_LANCZOS4)
                if scale_factor == 8:
                    SR_image = np.array(Image.fromarray((SR_image * 255).astype(np.uint8)))
                    SR_image = await self.upscale_x4(use_decoration, SR_image)

            
            result_img = Image.fromarray((SR_image * 255).astype(np.uint8))
            buffer = io.BytesIO()
            result_img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            
            return img_str
        except Exception as e:
            self.logger.log_error(e, "upscale_image")
            raise e

    async def upscale_x4(self, use_decoration, img_array):
        pre_image = await self.preprocessing(img_array)
            
        with torch.no_grad():
            SR_image = self.model(pre_image)

        SR_image = await self.postprocessing(SR_image, use_decoration)
        return SR_image

    async def postprocessing(self, SR_image, use_decoration: bool = False):
        SR_image = SR_image.squeeze(0).permute(1, 2, 0).cpu().numpy()
        SR_image= np.clip(SR_image, -1, 1)
        SR_image = SR_image * 0.5 + 0.5

        SR_image = np.clip(SR_image, 0, 1)

        if use_decoration:
            SR_image = cv2.bilateralFilter(SR_image, d=3, sigmaColor=75, sigmaSpace=75)
        return SR_image
    
    async def preprocessing(self, low_image):
        # Преобразуем изображение с помощью albumentations
        #low_transform = await self.transform.get_lowres_transform(low_image.shape)
        #preproc_image = low_transform(image=low_image)["image"]

        preproc_image = self.transform.original_transform(image=low_image)["image"]
        # Добавляем batch dimension и перемещаем на устройство (GPU/CPU)
        preproc_image = preproc_image.unsqueeze(0).to(self.device)

        return preproc_image
        
    def is_ready(self) -> bool:
        """Проверка готовности модели"""
        return self.ready 