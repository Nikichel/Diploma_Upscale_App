import albumentations as A
from albumentations.pytorch import ToTensorV2
from PIL import Image

class Transforms:
    def __init__(self, high_res = 256, low_res_scale_factor=4):
        self.high_res = high_res
        self.low_res_scale_factor = low_res_scale_factor

        self.original_transform = A.Compose(
            [
                A.Normalize(mean=[0, 0, 0], std=[1, 1, 1]),
                ToTensorV2(),
            ]
        )

    async def get_lowres_transform(self, image_shape):
        """
        Создает преобразования для low-res изображений на основе размера входного изображения.
        """
        low_res_width = max(image_shape[1] // self.low_res_scale_factor, 1)
        low_res_height = max(image_shape[0] // self.low_res_scale_factor, 1)
        # print(f"{low_res_width}\n {low_res_height}")
        return A.Compose(
            [
                A.Resize(width=low_res_width, height=low_res_height, interpolation=Image.BICUBIC),
                A.Normalize(mean=[0, 0, 0], std=[1, 1, 1]),
                ToTensorV2(),
            ]
        )