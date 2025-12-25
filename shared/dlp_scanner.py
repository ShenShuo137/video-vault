"""
DLP扫描模块
使用OCR识别视频帧中的文字，并检测敏感信息
"""
import re
import cv2
import numpy as np
from shared.config import SENSITIVE_PATTERNS, Config
from shared.ocr_service import OCRService


class DLPScanner:
    """DLP扫描器 - 检测敏感信息"""

    def __init__(self, confidence_threshold=None):
        """
        初始化
        :param confidence_threshold: OCR识别置信度阈值
        """
        self.confidence_threshold = confidence_threshold or Config.OCR_CONFIDENCE_THRESHOLD
        self.patterns = SENSITIVE_PATTERNS
        self.ocr_service = OCRService()  # 使用OCR服务抽象层

    def ocr_extract_text(self, image):
        """
        使用OCR提取图像中的文字
        :param image: OpenCV图像(numpy array)
        :return: OCR结果列表 [{'text': str, 'confidence': float, 'bbox': tuple}, ...]
        """
        # 直接使用OCR服务（会自动选择本地或云端）
        results = self.ocr_service.extract_text(image)

        # 已经过滤过置信度，直接返回
        return results

    def _legacy_ocr_extract_text(self, image):
        """
        【已废弃】原本地Tesseract实现
        保留用于参考，实际不再使用
        """
        # 将OpenCV图像转换为PIL图像
        if isinstance(image, np.ndarray):
            # OpenCV使用BGR，PIL使用RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image_rgb)
        else:
            pil_image = image

        # 使用pytesseract进行OCR
        # 返回详细信息: text, confidence, bbox
        import pytesseract
        from PIL import Image
        ocr_data = pytesseract.image_to_data(pil_image, lang='eng+chi_sim', output_type=pytesseract.Output.DICT)

        results = []
        n_boxes = len(ocr_data['text'])

        for i in range(n_boxes):
            text = ocr_data['text'][i].strip()
            conf = float(ocr_data['conf'][i]) / 100.0 if ocr_data['conf'][i] != -1 else 0.0

            # 过滤空文本和低置信度
            if text and conf >= self.confidence_threshold:
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                bbox = (x, y, w, h)

                results.append({
                    'text': text,
                    'confidence': conf,
                    'bbox': bbox
                })

        return results

    def detect_sensitive_info(self, text):
        """
        检测文本中的敏感信息
        :param text: 待检测的文本
        :return: 检测结果列表 [(type, matched_text), ...]
        """
        detections = []

        for sensitive_type, pattern in self.patterns.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                detections.append({
                    'type': sensitive_type,
                    'matched_text': match.group(0),
                    'start': match.start(),
                    'end': match.end()
                })

        return detections

    def scan_frame(self, frame):
        """
        扫描单个视频帧
        :param frame: OpenCV图像
        :return: 检测结果字典
        """
        # Step 1: OCR提取文字
        ocr_results = self.ocr_extract_text(frame)

        # Step 2: 检测敏感信息
        sensitive_detections = []

        for ocr_item in ocr_results:
            text = ocr_item['text']
            detections = self.detect_sensitive_info(text)

            for detection in detections:
                sensitive_detections.append({
                    'ocr_text': text,
                    'ocr_confidence': ocr_item['confidence'],
                    'bbox': ocr_item['bbox'],
                    'sensitive_type': detection['type'],
                    'matched_text': detection['matched_text']
                })

        return {
            'ocr_count': len(ocr_results),
            'sensitive_count': len(sensitive_detections),
            'detections': sensitive_detections
        }

    def scan_video_frames(self, frames):
        """
        扫描多个视频帧
        :param frames: 帧列表 [(frame_id, timestamp, frame_image), ...]
        :return: 扫描结果列表
        """
        results = []

        for frame_id, timestamp, frame in frames:
            print(f"扫描帧 {frame_id} (时间={timestamp:.2f}s)...")
            scan_result = self.scan_frame(frame)

            if scan_result['sensitive_count'] > 0:
                results.append({
                    'frame_id': frame_id,
                    'timestamp': timestamp,
                    'frame': frame,
                    'scan_result': scan_result
                })
                print(f"  ⚠️  发现 {scan_result['sensitive_count']} 个敏感信息!")

        print(f"扫描完成: {len(frames)} 帧，发现 {len(results)} 帧包含敏感信息")
        return results


class SensitiveInfoMasker:
    """敏感信息脱敏处理器"""

    def __init__(self, blur_intensity=51):
        """
        初始化
        :param blur_intensity: 高斯模糊强度(必须是奇数)
        """
        self.blur_intensity = blur_intensity if blur_intensity % 2 == 1 else blur_intensity + 1

    def apply_gaussian_blur(self, image, bbox, padding=10):
        """
        对指定区域应用高斯模糊
        :param image: 原始图像
        :param bbox: 边界框 (x, y, w, h)
        :param padding: 边界框扩展像素
        :return: 处理后的图像
        """
        x, y, w, h = bbox
        height, width = image.shape[:2]

        # 扩展边界框
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(width, x + w + padding)
        y2 = min(height, y + h + padding)

        # 提取区域
        roi = image[y1:y2, x1:x2]

        # 应用高斯模糊
        blurred_roi = cv2.GaussianBlur(roi, (self.blur_intensity, self.blur_intensity), 0)

        # 替换回原图
        result = image.copy()
        result[y1:y2, x1:x2] = blurred_roi

        return result

    def apply_mosaic(self, image, bbox, mosaic_size=20, padding=10):
        """
        对指定区域应用马赛克
        :param image: 原始图像
        :param bbox: 边界框 (x, y, w, h)
        :param mosaic_size: 马赛克块大小
        :param padding: 边界框扩展像素
        :return: 处理后的图像
        """
        x, y, w, h = bbox
        height, width = image.shape[:2]

        # 扩展边界框
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(width, x + w + padding)
        y2 = min(height, y + h + padding)

        # 提取区域
        roi = image[y1:y2, x1:x2]

        # 应用马赛克效果
        small = cv2.resize(roi, (mosaic_size, mosaic_size), interpolation=cv2.INTER_LINEAR)
        mosaic_roi = cv2.resize(small, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)

        # 替换回原图
        result = image.copy()
        result[y1:y2, x1:x2] = mosaic_roi

        return result

    def mask_frame(self, frame, detections, method='blur'):
        """
        对帧中的敏感信息进行脱敏处理
        :param frame: 原始帧
        :param detections: 检测结果列表
        :param method: 脱敏方法 'blur' 或 'mosaic'
        :return: 处理后的帧
        """
        result = frame.copy()

        for detection in detections:
            bbox = detection['bbox']

            if method == 'blur':
                result = self.apply_gaussian_blur(result, bbox)
            elif method == 'mosaic':
                result = self.apply_mosaic(result, bbox)

        return result
