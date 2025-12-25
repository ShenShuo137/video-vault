"""
配置管理模块
从环境变量加载配置
"""
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()


class Config:
    """配置类"""

    # 华为云配置
    HUAWEI_CLOUD_AK = os.getenv('HUAWEI_CLOUD_AK', '')
    HUAWEI_CLOUD_SK = os.getenv('HUAWEI_CLOUD_SK', '')
    HUAWEI_CLOUD_REGION = os.getenv('HUAWEI_CLOUD_REGION', 'cn-north-4')

    # OBS对象存储配置
    OBS_BUCKET_NAME = os.getenv('OBS_BUCKET_NAME', 'video-vault-storage')
    OBS_ENDPOINT = os.getenv('OBS_ENDPOINT', 'obs.cn-north-4.myhuaweicloud.com')

    # RDS数据库配置
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '3306'))
    DB_NAME = os.getenv('DB_NAME', 'video_vault')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')

    # AI大模型API配置
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')
    LLM_API_BASE = os.getenv('LLM_API_BASE', 'https://api.openai.com/v1')
    LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4')

    # 华为云OCR服务配置
    OCR_ENDPOINT = os.getenv('OCR_ENDPOINT', 'https://ocr.cn-north-4.myhuaweicloud.com')
    OCR_PROJECT_ID = os.getenv('OCR_PROJECT_ID', '')

    # 本地测试配置
    LOCAL_MODE = os.getenv('LOCAL_MODE', 'true').lower() == 'true'
    LOCAL_STORAGE_PATH = os.getenv('LOCAL_STORAGE_PATH', './local_tests/storage')

    # DLP配置
    SLICE_DURATION = int(os.getenv('SLICE_DURATION', '60'))  # 视频切片时长(秒)
    OCR_CONFIDENCE_THRESHOLD = float(os.getenv('OCR_CONFIDENCE_THRESHOLD', '0.6'))  # OCR置信度阈值
    BLUR_INTENSITY = int(os.getenv('BLUR_INTENSITY', '51'))  # 高斯模糊强度

    # Serverless函数URN配置（用于函数间调用）
    DLP_SCANNER_FUNCTION_URN = os.getenv('DLP_SCANNER_FUNCTION_URN', '')
    VIDEO_MERGER_FUNCTION_URN = os.getenv('VIDEO_MERGER_FUNCTION_URN', '')

    # 华为云MPC配置
    MPC_ENDPOINT = os.getenv('MPC_ENDPOINT', 'https://mpc.cn-north-4.myhuaweicloud.com')
    MPC_PROJECT_ID = os.getenv('MPC_PROJECT_ID', '')

    @classmethod
    def validate(cls):
        """验证必需的配置项"""
        missing = []

        if not cls.LOCAL_MODE:
            if not cls.HUAWEI_CLOUD_AK:
                missing.append('HUAWEI_CLOUD_AK')
            if not cls.HUAWEI_CLOUD_SK:
                missing.append('HUAWEI_CLOUD_SK')
            if not cls.DB_PASSWORD:
                missing.append('DB_PASSWORD')

        if missing:
            raise ValueError(f"缺少必需的环境变量: {', '.join(missing)}")

        return True


# 敏感信息检测规则
SENSITIVE_PATTERNS = {
    'openai_key': r'sk-[A-Za-z0-9]{48}',
    'aws_key': r'AKIA[0-9A-Z]{16}',
    'huawei_ak': r'[A-Z0-9]{20}',
    'password': r'password[:\s=]+\S+',
    'id_card': r'\d{17}[\dXx]',
    'phone': r'1[3-9]\d{9}',
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'credit_card': r'\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}',
}
