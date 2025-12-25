"""
华为云FunctionGraph入口 - DLP扫描函数
触发方式: 被video_slicer函数调用（异步）
"""
import json
import os
import sys

sys.path.insert(0, '/opt/python')
sys.path.insert(0, os.path.dirname(__file__))

from shared.video_slicer import VideoSlicer
from shared.dlp_scanner import DLPScanner, SensitiveInfoMasker
from shared.obs_helper import OBSHelper
from shared.db_connector import AuditLogDAO
from shared.config import Config
import cv2


def handler(event, context):
    """
    DLP扫描函数Handler

    event结构:
    {
        "video_id": "abc-123-def",
        "slice_index": 0,
        "slice_key": "slices/abc-123-def/slice_0000.mp4",
        "bucket_name": "video-vault-storage",
        "total_slices": 3
    }

    :param event: 调用事件
    :param context: FunctionGraph上下文
    :return: 处理结果
    """
    logger = context.getLogger()
    logger.info(f"收到DLP扫描任务: {json.dumps(event)}")

    try:
        video_id = event['video_id']
        slice_index = event['slice_index']
        slice_key = event['slice_key']
        bucket_name = event['bucket_name']
        total_slices = event['total_slices']

        # 初始化
        obs_helper = OBSHelper()
        slicer = VideoSlicer()
        scanner = DLPScanner(confidence_threshold=Config.OCR_CONFIDENCE_THRESHOLD)
        masker = SensitiveInfoMasker(blur_intensity=Config.BLUR_INTENSITY)

        # 尝试初始化数据库DAO（可选，完全容错）
        db_enabled = False
        audit_dao = None

        # 检查是否配置了数据库环境变量
        if os.getenv('DB_HOST') and os.getenv('DB_PASSWORD'):
            try:
                audit_dao = AuditLogDAO()
                # 尝试测试连接（避免延迟失败）
                audit_dao.connection.ping(reconnect=True)
                db_enabled = True
                logger.info("数据库连接成功")
            except Exception as e:
                logger.warning(f"数据库未配置或连接失败，将跳过数据库写入: {e}")
                audit_dao = None
                db_enabled = False
        else:
            logger.info("未配置数据库环境变量（DB_HOST/DB_PASSWORD），跳过数据库操作")

        # 下载切片
        local_slice_path = f"/tmp/{video_id}_slice_{slice_index}.mp4"
        obs_helper.download_file(slice_key, local_slice_path)

        logger.info(f"切片已下载: {local_slice_path}")

        # 提取关键帧
        frames = slicer.extract_keyframes(local_slice_path, interval=1.0)
        logger.info(f"提取了 {len(frames)} 个关键帧")

        # 扫描关键帧
        scan_results = scanner.scan_video_frames(frames)

        if not scan_results:
            logger.info("未发现敏感信息，直接使用原切片")

            # 上传原切片到processed目录
            processed_key = f"processed/{video_id}/slice_{slice_index:04d}.mp4"
            obs_helper.upload_file(local_slice_path, processed_key)

            # 清理
            os.remove(local_slice_path)

            # 检查是否所有切片都处理完成，触发合并
            _check_and_trigger_merge(video_id, slice_index, total_slices, context)

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "video_id": video_id,
                    "slice_index": slice_index,
                    "sensitive_count": 0
                })
            }

        # 发现敏感信息，处理视频
        logger.info(f"发现 {len(scan_results)} 帧包含敏感信息")

        # 创建敏感帧映射
        sensitive_frames = {result['frame_id']: result for result in scan_results}

        # 逐帧处理视频
        processed_slice_path = f"/tmp/{video_id}_processed_{slice_index}.mp4"
        _process_slice_video(local_slice_path, processed_slice_path, sensitive_frames, masker)

        logger.info(f"切片脱敏完成: {processed_slice_path}")

        # 上传处理后的切片
        processed_key = f"processed/{video_id}/slice_{slice_index:04d}.mp4"
        obs_helper.upload_file(processed_slice_path, processed_key)

        # ✅ 新增：保存审计日志到OBS（供前端Serverless查询）
        _save_audit_log_to_obs(video_id, slice_index, scan_results, obs_helper, logger)

        # 记录审计日志到数据库（可选）
        total_sensitive_count = 0
        for result in scan_results:
            total_sensitive_count += result['scan_result']['sensitive_count']

            # 写入数据库（如果启用）
            if db_enabled and audit_dao:
                try:
                    for detection in result['scan_result']['detections']:
                        bbox = detection['bbox']
                        audit_dao.create_audit_log(
                            video_id=video_id,
                            slice_index=slice_index,
                            frame_id=result['frame_id'],
                            timestamp_in_video=result['timestamp'],
                            sensitive_type=detection['sensitive_type'],
                            detected_text=detection['ocr_text'][:100],
                            confidence=detection['ocr_confidence'],
                            bbox_x=bbox[0],
                            bbox_y=bbox[1],
                            bbox_width=bbox[2],
                            bbox_height=bbox[3]
                        )
                except Exception as e:
                    logger.warning(f"写入数据库失败: {e}")

        # 清理临时文件
        os.remove(local_slice_path)
        os.remove(processed_slice_path)

        logger.info(f"切片 {slice_index} 处理完成，检测到 {total_sensitive_count} 个敏感信息")

        # 检查是否所有切片都处理完成，触发合并
        _check_and_trigger_merge(video_id, slice_index, total_slices, context)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "video_id": video_id,
                "slice_index": slice_index,
                "sensitive_count": total_sensitive_count
            })
        }

    except Exception as e:
        logger.error(f"DLP扫描失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }


def _process_slice_video(input_path, output_path, sensitive_frames, masker):
    """处理单个切片视频，对敏感帧进行脱敏"""
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frame_id = 0
    interval_frames = int(fps * 1.0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        keyframe_id = frame_id // interval_frames
        if keyframe_id in sensitive_frames:
            result = sensitive_frames[keyframe_id]
            detections = result['scan_result']['detections']
            frame = masker.mask_frame(frame, detections, method='blur')

        out.write(frame)
        frame_id += 1

    cap.release()
    out.release()


def _check_and_trigger_merge(video_id, slice_index, total_slices, context):
    """检查是否所有切片都处理完成，如果是则触发合并函数"""
    logger = context.getLogger()

    # 这里简化处理：最后一个切片处理完成时触发合并
    # 注：实际生产环境应该用分布式锁和计数器（如Redis）来跟踪进度
    if slice_index == total_slices - 1:
        logger.info(f"所有切片处理完成，触发合并函数")

        # 调用合并函数
        from huaweicloudsdkfunctiongraph.v2 import FunctionGraphClient
        from huaweicloudsdkfunctiongraph.v2.region.functiongraph_region import FunctionGraphRegion
        from huaweicloudsdkfunctiongraph.v2.model import InvokeFunctionRequest
        from huaweicloudsdkcore.auth.credentials import BasicCredentials

        credentials = BasicCredentials(Config.HUAWEI_CLOUD_AK, Config.HUAWEI_CLOUD_SK)
        fg_client = FunctionGraphClient.new_builder() \
            .with_credentials(credentials) \
            .with_region(FunctionGraphRegion.value_of(Config.HUAWEI_CLOUD_REGION)) \
            .build()

        merge_payload = {
            "video_id": video_id,
            "total_slices": total_slices,
            "bucket_name": "video-vault-storage"
        }

        request = InvokeFunctionRequest()
        request.function_urn = Config.VIDEO_MERGER_FUNCTION_URN
        request.body = merge_payload

        fg_client.invoke_function(request)

        logger.info(f"已触发视频合并函数")


def _save_audit_log_to_obs(video_id, slice_index, scan_results, obs_helper, logger):
    """
    保存审计日志到OBS（供前端Serverless架构查询）

    :param video_id: 视频ID
    :param slice_index: 切片索引
    :param scan_results: 扫描结果列表
    :param obs_helper: OBS Helper实例
    :param logger: Logger实例
    """
    try:
        import tempfile

        audit_log_key = f"logs/{video_id}_audit.json"
        temp_log_path = f"/tmp/audit_{video_id}.json"

        # 尝试下载现有日志
        audit_data = {
            'video_id': video_id,
            'detections': [],
            'total_detections': 0
        }

        try:
            obs_helper.download_file(audit_log_key, temp_log_path)
            with open(temp_log_path, 'r', encoding='utf-8') as f:
                audit_data = json.load(f)
        except Exception:
            # 文件不存在，使用初始数据
            pass

        # 添加新的检测记录
        for result in scan_results:
            for detection in result['scan_result']['detections']:
                bbox = detection['bbox']
                audit_entry = {
                    'slice_index': slice_index,
                    'frame_id': result['frame_id'],
                    'timestamp': result['timestamp'],
                    'type': detection['sensitive_type'],
                    'text': detection['ocr_text'][:100] if detection.get('ocr_text') else '',
                    'confidence': detection.get('ocr_confidence', 0),
                    'bbox': {
                        'x': bbox[0],
                        'y': bbox[1],
                        'width': bbox[2],
                        'height': bbox[3]
                    }
                }
                audit_data['detections'].append(audit_entry)

        # 更新总数
        audit_data['total_detections'] = len(audit_data['detections'])

        # 保存到临时文件
        with open(temp_log_path, 'w', encoding='utf-8') as f:
            json.dump(audit_data, f, ensure_ascii=False, indent=2)

        # 上传到OBS
        obs_helper.upload_file(temp_log_path, audit_log_key)
        logger.info(f"审计日志已保存到OBS: {audit_log_key}")

        # 清理临时文件
        if os.path.exists(temp_log_path):
            os.remove(temp_log_path)

    except Exception as e:
        logger.error(f"保存审计日志到OBS失败: {str(e)}")
        # 不影响主流程，继续执行
