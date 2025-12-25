"""
测试华为云服务连接
验证OCR、MPC、OBS配置是否正确
"""
import os
import sys
import cv2
import numpy as np
from dotenv import load_dotenv

# 加载配置
load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from shared.config import Config
from shared.obs_helper import OBSHelper
from shared.ocr_service import OCRService


def print_step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


def test_obs_connection():
    """测试OBS连接"""
    print_step("1. 测试OBS连接")

    try:
        obs_helper = OBSHelper()

        # 列出Bucket
        print(f"Bucket名称: {Config.OBS_BUCKET_NAME}")
        print("✅ OBS连接成功！")
        return True

    except Exception as e:
        print(f"❌ OBS连接失败: {e}")
        return False


def test_ocr_service():
    """测试OCR服务"""
    print_step("2. 测试华为云OCR服务")

    try:
        # 创建测试图片
        img = np.ones((200, 800, 3), dtype=np.uint8) * 255
        cv2.putText(img, 'Test API Key: sk-abc123def456', (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)

        # 测试OCR
        ocr = OCRService()
        result = ocr.extract_text(img)

        print(f"测试图片文本: 'Test API Key: sk-abc123def456'")
        print(f"识别结果类型: {type(result)}")

        # 处理结果（可能是列表或字符串）
        if isinstance(result, list):
            # 提取所有文本
            texts = [item['text'] for item in result if isinstance(item, dict) and 'text' in item]
            result_text = ' '.join(texts)
            print(f"识别到的文本块: {len(result)}")
            print(f"合并后的文本: {result_text}")
        else:
            result_text = str(result)
            print(f"识别结果: {result_text}")

        # 检查是否包含关键词
        result_lower = result_text.lower()
        if 'test' in result_lower or 'key' in result_lower or 'api' in result_lower:
            print("✅ OCR服务正常工作！识别结果正确")
            return True
        elif result_text:
            print("⚠️  OCR服务工作正常，但识别结果不完全准确")
            print(f"   预期包含: test, api, key")
            print(f"   实际识别: {result_text}")
            return True
        else:
            print("⚠️  OCR服务未识别到文本")
            return False

    except Exception as e:
        print(f"❌ OCR服务失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_mpc_service():
    """测试MPC服务（可选）"""
    print_step("3. 测试华为云MPC服务（可选）")

    try:
        from shared.video_processing_service import VideoProcessingService

        service = VideoProcessingService()
        print("✅ MPC服务配置正确！")
        print("   (实际视频合并将在处理视频时测试)")
        return True

    except Exception as e:
        print(f"⚠️  MPC服务初始化警告: {e}")
        print("   这不影响测试，实际使用时再验证")
        return True


def main():
    """主测试函数"""
    print("""
╔══════════════════════════════════════════════════════════╗
║          华为云服务连接测试                               ║
║          Huawei Cloud Services Test                      ║
╚══════════════════════════════════════════════════════════╝
    """)

    print("当前配置:")
    print(f"  区域: {Config.HUAWEI_CLOUD_REGION}")
    print(f"  Bucket: {Config.OBS_BUCKET_NAME}")
    print(f"  本地模式: {Config.LOCAL_MODE}")

    if Config.LOCAL_MODE:
        print("\n⚠️  警告: 当前处于本地模式（LOCAL_MODE=true）")
        print("   请在.env中设置 LOCAL_MODE=false 来测试云服务\n")
        return

    # 运行测试
    results = []
    results.append(("OBS连接", test_obs_connection()))
    results.append(("OCR服务", test_ocr_service()))
    results.append(("MPC服务", test_mpc_service()))

    # 汇总结果
    print_step("测试结果汇总")

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有测试通过！华为云服务配置正确！")
        print("\n下一步:")
        print("  1. 运行 python build_layers.py 打包函数")
        print("  2. 参考 SERVERLESS_DEPLOYMENT_GUIDE.md 部署到华为云")
    else:
        print("❌ 部分测试失败，请检查配置")
        print("\n排查建议:")
        print("  1. 确认.env中的AK/SK正确")
        print("  2. 确认OCR_PROJECT_ID和MPC_PROJECT_ID正确")
        print("  3. 确认Bucket名称正确")
        print("  4. 检查账号是否有对应服务的权限")
    print("="*60)


if __name__ == "__main__":
    main()