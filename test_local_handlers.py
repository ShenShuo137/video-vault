#!/usr/bin/env python3
"""
华为云函数本地测试脚本
模拟FunctionGraph环境，在本地测试云函数逻辑
"""
import os
import sys
import json
import logging
from unittest.mock import Mock

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

# 设置本地模式（避免实际调用云服务）
os.environ['LOCAL_MODE'] = 'false'  # 设置为false以测试真实云服务调用

# 导入云函数handlers
from functions import video_slicer_handler
from functions import dlp_scanner_handler
from functions import video_merger_handler


class MockContext:
    """模拟FunctionGraph Context对象"""

    def __init__(self, function_name):
        self.function_name = function_name
        self.request_id = "test-request-id-12345"
        self.logger = logging.getLogger(function_name)
        self.logger.setLevel(logging.INFO)

        # 配置日志格式
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            f'[{function_name}] %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def getLogger(self):
        """获取logger"""
        return self.logger

    def get_request_id(self):
        """获取请求ID"""
        return self.request_id


def test_video_slicer_handler(test_video_path):
    """
    测试视频切片函数

    :param test_video_path: 本地测试视频路径
    """
    print("\n" + "="*70)
    print("测试 1: Video Slicer Handler")
    print("="*70)

    # 首先上传测试视频到OBS
    from shared.obs_helper import OBSHelper
    obs_helper = OBSHelper()

    # 上传测试视频
    test_video_name = os.path.basename(test_video_path)
    obs_key = f"uploads/test/{test_video_name}"

    print(f"\n上传测试视频到OBS: {obs_key}")
    upload_success = obs_helper.upload_file(test_video_path, obs_key)

    if not upload_success:
        print("❌ 测试视频上传失败，请检查OBS配置")
        return None

    print("✅ 测试视频上传成功")

    # 构造OBS触发事件
    event = {
        "Records": [{
            "eventName": "ObjectCreated:Put",
            "obs": {
                "bucket": {
                    "name": os.getenv('OBS_BUCKET_NAME')
                },
                "object": {
                    "key": obs_key,
                    "size": os.path.getsize(test_video_path)
                }
            }
        }]
    }

    # 创建模拟context
    context = MockContext("video-slicer")

    try:
        # 调用handler
        print("\n调用video_slicer_handler...")
        result = video_slicer_handler.handler(event, context)

        print(f"\n返回结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result['statusCode'] == 200:
            body = json.loads(result['body'])
            print(f"\n✅ 测试通过!")
            print(f"   - 视频ID: {body['video_id']}")
            print(f"   - 切片数量: {body['slice_count']}")
            print(f"   - 切片keys: {body['slice_keys'][:3]}...")
            return body
        else:
            print(f"\n❌ 测试失败: {result}")
            return None

    except Exception as e:
        print(f"\n❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_dlp_scanner_handler(video_id, slice_keys):
    """
    测试DLP扫描函数

    :param video_id: 视频ID
    :param slice_keys: 切片keys列表
    """
    print("\n" + "="*70)
    print("测试 2: DLP Scanner Handler")
    print("="*70)

    # 测试第一个切片
    test_slice_index = 0
    test_slice_key = slice_keys[test_slice_index]

    # 构造调用事件
    event = {
        "video_id": video_id,
        "slice_index": test_slice_index,
        "slice_key": test_slice_key,
        "bucket_name": os.getenv('OBS_BUCKET_NAME'),
        "total_slices": len(slice_keys)
    }

    # 创建模拟context
    context = MockContext("dlp-scanner")

    try:
        # 调用handler
        print(f"\n处理切片 {test_slice_index}: {test_slice_key}")
        result = dlp_scanner_handler.handler(event, context)

        print(f"\n返回结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result['statusCode'] == 200:
            body = json.loads(result['body'])
            print(f"\n✅ 测试通过!")
            print(f"   - 视频ID: {body['video_id']}")
            print(f"   - 切片索引: {body['slice_index']}")
            print(f"   - 敏感信息数量: {body['sensitive_count']}")
            return body
        else:
            print(f"\n❌ 测试失败: {result}")
            return None

    except Exception as e:
        print(f"\n❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_video_merger_handler(video_id, total_slices):
    """
    测试视频合并函数

    :param video_id: 视频ID
    :param total_slices: 切片总数
    """
    print("\n" + "="*70)
    print("测试 3: Video Merger Handler")
    print("="*70)

    # 构造调用事件
    event = {
        "video_id": video_id,
        "total_slices": total_slices,
        "bucket_name": os.getenv('OBS_BUCKET_NAME')
    }

    # 创建模拟context
    context = MockContext("video-merger")

    try:
        # 调用handler
        print(f"\n合并 {total_slices} 个切片...")
        result = video_merger_handler.handler(event, context)

        print(f"\n返回结果:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        if result['statusCode'] == 200:
            body = json.loads(result['body'])
            print(f"\n✅ 测试通过!")
            print(f"   - 视频ID: {body['video_id']}")
            print(f"   - 输出key: {body['output_key']}")
            print(f"   - 状态: {body['status']}")
            return body
        else:
            print(f"\n❌ 测试失败: {result}")
            return None

    except Exception as e:
        print(f"\n❌ 异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def run_full_pipeline_test(test_video_path):
    """
    运行完整的处理流程测试

    :param test_video_path: 测试视频路径
    """
    print("""
╔══════════════════════════════════════════════════════════════════╗
║           华为云函数本地测试 - 完整流程                          ║
║           Local Handler Test - Full Pipeline                     ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    # 验证测试视频
    if not os.path.exists(test_video_path):
        print(f"❌ 测试视频不存在: {test_video_path}")
        print("\n请提供一个测试视频文件，例如:")
        print("   python test_local_handlers.py test_video.mp4")
        return False

    print(f"📹 测试视频: {test_video_path}")
    print(f"   大小: {os.path.getsize(test_video_path) / (1024*1024):.2f} MB")

    # 验证环境配置
    print("\n检查环境配置...")
    required_vars = ['HUAWEI_CLOUD_AK', 'HUAWEI_CLOUD_SK', 'OBS_BUCKET_NAME']
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
            print(f"   ❌ {var}: 未配置")
        else:
            print(f"   ✅ {var}: 已配置")

    if missing:
        print(f"\n❌ 缺少配置: {', '.join(missing)}")
        print("   请在 .env 文件中配置这些变量")
        return False

    # 测试1: 视频切片
    slicer_result = test_video_slicer_handler(test_video_path)
    if not slicer_result:
        print("\n❌ 视频切片测试失败，终止测试")
        return False

    video_id = slicer_result['video_id']
    slice_keys = slicer_result['slice_keys']

    # 测试2: DLP扫描（测试第一个切片）
    scanner_result = test_dlp_scanner_handler(video_id, slice_keys)
    if not scanner_result:
        print("\n❌ DLP扫描测试失败，终止测试")
        return False

    # 为了完整测试合并功能，需要处理所有切片
    # 在实际测试中，我们模拟所有切片都已处理完成
    print("\n⏭️  跳过其他切片处理（生产环境会并行处理）")

    # 手动处理剩余切片（简化版）
    print(f"\n处理剩余 {len(slice_keys) - 1} 个切片...")
    from shared.obs_helper import OBSHelper
    obs_helper = OBSHelper()

    for i, slice_key in enumerate(slice_keys):
        if i == 0:
            continue  # 已处理

        # 直接复制到processed目录（跳过实际扫描）
        processed_key = f"processed/{video_id}/slice_{i:04d}.mp4"
        print(f"   处理切片 {i+1}/{len(slice_keys)}: {slice_key} -> {processed_key}")

        # 下载并重新上传（模拟处理）
        local_temp = f"/tmp/test_slice_{i}.mp4"
        obs_helper.download_file(slice_key, local_temp)
        obs_helper.upload_file(local_temp, processed_key)

        # 清理
        if os.path.exists(local_temp):
            os.remove(local_temp)

    print("✅ 所有切片已处理")

    # 测试3: 视频合并
    merger_result = test_video_merger_handler(video_id, len(slice_keys))
    if not merger_result:
        print("\n❌ 视频合并测试失败")
        return False

    # 测试完成
    print("\n" + "="*70)
    print("🎉 完整流程测试通过!")
    print("="*70)
    print(f"\n最终输出视频: {merger_result['output_key']}")
    print("\n可以下载查看结果:")
    print(f"   OBS路径: obs://{os.getenv('OBS_BUCKET_NAME')}/{merger_result['output_key']}")

    return True


def test_single_handler():
    """单独测试某个handler（交互模式）"""
    print("""
请选择要测试的函数:
  1. Video Slicer (视频切片)
  2. DLP Scanner (DLP扫描)
  3. Video Merger (视频合并)
  0. 退出
    """)

    choice = input("请输入选项 (1/2/3/0): ").strip()

    if choice == "1":
        test_video_path = input("请输入测试视频路径: ").strip()
        test_video_slicer_handler(test_video_path)
    elif choice == "2":
        video_id = input("请输入视频ID: ").strip()
        slice_key = input("请输入切片key: ").strip()
        total_slices = int(input("请输入总切片数: ").strip())
        test_dlp_scanner_handler(video_id, [slice_key])
    elif choice == "3":
        video_id = input("请输入视频ID: ").strip()
        total_slices = int(input("请输入总切片数: ").strip())
        test_video_merger_handler(video_id, total_slices)
    else:
        print("退出")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 命令行模式: python test_local_handlers.py test_video.mp4
        test_video_path = sys.argv[1]
        success = run_full_pipeline_test(test_video_path)
        sys.exit(0 if success else 1)
    else:
        # 交互模式
        print("""
使用方法:
  1. 完整流程测试: python test_local_handlers.py <测试视频路径>
  2. 单独测试: python test_local_handlers.py
        """)

        choice = input("\n选择模式 (1=完整测试, 2=单独测试): ").strip()

        if choice == "1":
            test_video_path = input("请输入测试视频路径: ").strip()
            run_full_pipeline_test(test_video_path)
        elif choice == "2":
            test_single_handler()
        else:
            print("无效选择")
