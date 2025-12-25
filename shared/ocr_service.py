"""
OCR服务抽象层
支持本地Tesseract和华为云OCR无缝切换
"""
import os
import cv2
import numpy as np
import base64
from shared.config import Config


class OCRService:
    """OCR服务 - 自动选择本地或云端"""

    def __init__(self):
        self.use_cloud = not Config.LOCAL_MODE
        print(f"OCR模式: {'华为云OCR' if self.use_cloud else '本地Tesseract'}")

    def extract_text(self, image):
        """
        统一的OCR接口
        :param image: OpenCV图像(numpy array)
        :return: OCR结果列表 [{'text': str, 'confidence': float, 'bbox': tuple}, ...]
        """
        if self.use_cloud:
            return self._huawei_ocr(image)
        else:
            return self._tesseract_ocr(image)

    def _tesseract_ocr(self, image):
        """本地Tesseract OCR"""
        try:
            import pytesseract
            from PIL import Image

            # 尝试配置Tesseract路径
            tesseract_paths = [
                r'D:\Tesseract\tesseract.exe',  # 用户自定义路径
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                r'C:\Windows\System32\tesseract.exe',
                '/usr/bin/tesseract',
                '/usr/local/bin/tesseract'
            ]

            for path in tesseract_paths:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    break

            # 转换图像格式
            if isinstance(image, np.ndarray):
                image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(image_rgb)
            else:
                pil_image = image

            # OCR识别
            data = pytesseract.image_to_data(
                pil_image,
                lang='eng+chi_sim',
                output_type=pytesseract.Output.DICT
            )

            # 格式化结果
            results = []
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                text = data['text'][i].strip()
                conf = float(data['conf'][i]) / 100.0 if data['conf'][i] != -1 else 0.0

                if text and conf >= Config.OCR_CONFIDENCE_THRESHOLD:
                    results.append({
                        'text': text,
                        'confidence': conf,
                        'bbox': (
                            data['left'][i],
                            data['top'][i],
                            data['width'][i],
                            data['height'][i]
                        )
                    })

            return results

        except Exception as e:
            print(f"Tesseract OCR错误: {e}")
            return []

    def _huawei_ocr(self, image):
        """华为云OCR服务"""
        try:
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdkocr.v1.region.ocr_region import OcrRegion
            from huaweicloudsdkocr.v1 import OcrClient, RecognizeGeneralTextRequest, GeneralTextRequestBody

            # 初始化客户端
            credentials = BasicCredentials(Config.HUAWEI_CLOUD_AK, Config.HUAWEI_CLOUD_SK)
            client = OcrClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(OcrRegion.value_of(Config.HUAWEI_CLOUD_REGION)) \
                .build()

            # 将图像转为base64
            _, buffer = cv2.imencode('.jpg', image)
            image_base64 = base64.b64encode(buffer).decode('utf-8')

            # 调用通用文字识别API
            request = RecognizeGeneralTextRequest()
            request.body = GeneralTextRequestBody(image=image_base64)
            response = client.recognize_general_text(request)

            # 格式化结果
            results = []
            if response.result and response.result.words_block_list:
                for block in response.result.words_block_list:
                    # 华为云OCR置信度已经是0-1范围
                    if block.confidence >= Config.OCR_CONFIDENCE_THRESHOLD:
                        # 获取边界框 - 华为云返回的是location属性
                        location = block.location if hasattr(block, 'location') else None

                        if location and len(location) >= 4:
                            # location是一个包含4个点的列表: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                            # 左上角和右下角坐标
                            x = location[0][0]
                            y = location[0][1]
                            width = location[2][0] - location[0][0]
                            height = location[2][1] - location[0][1]
                        else:
                            # 如果没有location，使用默认值
                            x, y, width, height = 0, 0, 0, 0

                        results.append({
                            'text': block.words,
                            'confidence': block.confidence,
                            'bbox': (x, y, width, height)
                        })

            return results

        except Exception as e:
            print(f"华为云OCR错误: {e}")
            import traceback
            traceback.print_exc()
            # 如果云端失败，降级到本地
            print("降级使用本地Tesseract")
            return self._tesseract_ocr(image)
