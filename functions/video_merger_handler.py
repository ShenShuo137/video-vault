"""
华为云FunctionGraph入口 - 视频合并函数
触发方式: 被dlp_scanner函数调用（当所有切片处理完成时）
"""
import json
import os
import sys

sys.path.insert(0, '/opt/python')
sys.path.insert(0, os.path.dirname(__file__))

from shared.video_merger import VideoMerger
from shared.obs_helper import OBSHelper
from shared.db_connector import VideoDAO
from shared.config import Config


def handler(event, context):
    """
    视频合并函数Handler

    event结构:
    {
        "video_id": "abc-123-def",
        "total_slices": 3,
        "bucket_name": "video-vault-storage"
    }

    :param event: 调用事件
    :param context: FunctionGraph上下文
    :return: 处理结果
    """
    logger = context.getLogger()
    logger.info(f"收到视频合并任务: {json.dumps(event)}")

    try:
        video_id = event['video_id']
        total_slices = event['total_slices']
        bucket_name = event['bucket_name']

        # 初始化
        obs_helper = OBSHelper()
        merger = VideoMerger()

        # 尝试初始化数据库DAO（可选，完全容错）
        db_enabled = False
        video_dao = None

        # 检查是否配置了数据库环境变量
        if os.getenv('DB_HOST') and os.getenv('DB_PASSWORD'):
            try:
                video_dao = VideoDAO()
                # 尝试测试连接（避免延迟失败）
                video_dao.connection.ping(reconnect=True)
                db_enabled = True
                logger.info("数据库连接成功")
            except Exception as e:
                logger.warning(f"数据库未配置或连接失败，将跳过数据库写入: {e}")
                video_dao = None
                db_enabled = False
        else:
            logger.info("未配置数据库环境变量（DB_HOST/DB_PASSWORD），跳过数据库操作")

        # 下载所有处理后的切片
        slice_files = []
        for i in range(total_slices):
            slice_key = f"processed/{video_id}/slice_{i:04d}.mp4"
            local_slice_path = f"/tmp/{video_id}_slice_{i:04d}.mp4"

            obs_helper.download_file(slice_key, local_slice_path)
            slice_files.append(local_slice_path)

        logger.info(f"已下载 {len(slice_files)} 个切片")

        # 合并视频
        output_path = f"/tmp/{video_id}_sanitized.mp4"
        success = merger.merge(slice_files, output_path, use_ffmpeg=True)

        if not success:
            raise Exception("视频合并失败")

        logger.info(f"视频合并完成: {output_path}")

        # 上传合并后的视频到OBS
        output_key = f"outputs/{video_id}_sanitized.mp4"
        obs_helper.upload_file(output_path, output_key)

        logger.info(f"合并视频已上传: {output_key}")

        # 更新数据库状态（可选）
        if db_enabled and video_dao:
            try:
                video_dao.update_video_status(video_id, 'completed', output_url=f"obs://{bucket_name}/{output_key}")
                logger.info("数据库状态已更新")
            except Exception as e:
                logger.warning(f"更新数据库失败: {e}")

        # 清理临时文件
        for slice_file in slice_files:
            os.remove(slice_file)
        os.remove(output_path)

        logger.info(f"视频 {video_id} 处理完成")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "video_id": video_id,
                "output_key": output_key,
                "status": "completed"
            })
        }

    except Exception as e:
        logger.error(f"视频合并失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

        # 更新数据库状态为失败（可选）
        if db_enabled and video_dao:
            try:
                video_dao.update_video_status(video_id, 'failed')
            except Exception as db_error:
                logger.warning(f"更新数据库失败状态失败: {db_error}")

        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }
