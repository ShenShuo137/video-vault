"""
华为云FunctionGraph入口 - 视频切片函数
触发方式: OBS触发器（视频上传时自动触发）
"""
import json
import os
import sys

# ⚠️ 重要：先导入华为云运行时自带的 numpy（避免依赖层里的源码版本）
import numpy  # 使用华为云自带的 numpy

# 然后添加依赖层路径（用 append 而不是 insert，让系统路径优先）
sys.path.append('/opt/python')  # 依赖层路径
sys.path.insert(0, os.path.dirname(__file__))

from shared.video_slicer import VideoSlicer
from shared.obs_helper import OBSHelper
from shared.config import Config


def handler(event, context):
    """
    FunctionGraph Handler入口函数

    华为云OBS触发器事件格式（CloudEvents）:
    {
        "data": {
            "obs": {
                "bucket": {"name": "video-vault-storage"},
                "object": {
                    "key": "uploads/test_video.mp4",
                    "size": 1234567
                }
            },
            "eventName": "ObjectCreated:Put"
        }
    }

    :param event: OBS触发事件
    :param context: FunctionGraph上下文
    :return: 处理结果
    """
    logger = context.getLogger()
    logger.info(f"收到事件: {json.dumps(event)}")

    try:
        # 解析华为云OBS事件（CloudEvents格式）
        obs_data = event['data']['obs']
        bucket_name = obs_data['bucket']['name']
        object_key = obs_data['object']['key']

        logger.info(f"处理视频: {bucket_name}/{object_key}")

        # 生成视频ID
        video_id = object_key.split('/')[-1].replace('.mp4', '')

        # 初始化OBS Helper
        obs_helper = OBSHelper()

        # 下载视频到临时目录
        local_video_path = f"/tmp/{video_id}.mp4"
        obs_helper.download_file(object_key, local_video_path)

        logger.info(f"视频已下载: {local_video_path}")

        # 切片
        slicer = VideoSlicer(slice_duration=Config.SLICE_DURATION)
        slices_dir = f"/tmp/{video_id}_slices"
        os.makedirs(slices_dir, exist_ok=True)

        slice_files = slicer.slice_video(local_video_path, slices_dir)

        logger.info(f"切片完成: {len(slice_files)} 个切片")

        # 上传切片到OBS
        slice_keys = []
        for slice_file in slice_files:
            slice_name = os.path.basename(slice_file)
            slice_key = f"slices/{video_id}/{slice_name}"
            obs_helper.upload_file(slice_file, slice_key)
            slice_keys.append(slice_key)

        logger.info(f"切片已上传到OBS: {len(slice_keys)} 个")

        # 清理临时文件
        import shutil
        os.remove(local_video_path)
        shutil.rmtree(slices_dir)

        # 触发DLP扫描函数（并行）
        from huaweicloudsdkfunctiongraph.v2 import FunctionGraphClient
        from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion
        from huaweicloudsdkcore.auth.credentials import BasicCredentials

        credentials = BasicCredentials(Config.HUAWEI_CLOUD_AK, Config.HUAWEI_CLOUD_SK)
        fg_client = FunctionGraphClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(FunctionGraphRegion.value_of(Config.HUAWEI_CLOUD_REGION)) \
            .build()

        # 为每个切片调用DLP扫描函数
        for idx, slice_key in enumerate(slice_keys):
            invoke_payload = {
                "video_id": video_id,
                "slice_index": idx,
                "slice_key": slice_key,
                "bucket_name": bucket_name,
                "total_slices": len(slice_keys)
            }

            # 异步调用DLP扫描函数
            from huaweicloudsdkfunctiongraph.v2.model import InvokeFunctionRequest
            request = InvokeFunctionRequest()
            request.function_urn = Config.DLP_SCANNER_FUNCTION_URN
            request.body = invoke_payload

            fg_client.invoke_function(request)

        logger.info(f"已触发 {len(slice_keys)} 个DLP扫描函数")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "video_id": video_id,
                "slice_count": len(slice_keys),
                "slice_keys": slice_keys
            })
        }

    except Exception as e:
        logger.error(f"处理失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }
