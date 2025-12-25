"""
Video Vault 本地测试 - 完整DLP处理流程
演示从视频输入到脱敏输出的完整流程
"""
import os
import sys
import uuid
import json
import cv2
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.config import Config
from shared.video_slicer import VideoSlicer
from shared.dlp_scanner import DLPScanner, SensitiveInfoMasker
from shared.video_merger import VideoMerger
from shared.db_connector import VideoDAO, AuditLogDAO


class VideoVaultPipeline:
    """Video Vault 处理流水线"""

    def __init__(self, local_mode=True):
        """初始化"""
        self.local_mode = local_mode
        self.video_slicer = VideoSlicer(slice_duration=Config.SLICE_DURATION)
        self.dlp_scanner = DLPScanner(confidence_threshold=Config.OCR_CONFIDENCE_THRESHOLD)
        self.masker = SensitiveInfoMasker(blur_intensity=Config.BLUR_INTENSITY)
        self.video_merger = VideoMerger()

        # 如果不是本地模式，初始化数据库
        if not local_mode:
            self.video_dao = VideoDAO()
            self.audit_dao = AuditLogDAO()

        print("=" * 60)
        print("Video Vault DLP 处理流水线已初始化")
        print(f"运行模式: {'本地测试' if local_mode else '云端生产'}")
        print("=" * 60)

    def process_video(self, input_video_path, output_dir='./local_tests/output'):
        """
        处理单个视频的完整流程
        :param input_video_path: 输入视频路径
        :param output_dir: 输出目录
        :return: 处理结果
        """
        video_id = str(uuid.uuid4())
        video_title = os.path.basename(input_video_path)

        print(f"\n🎬 开始处理视频: {video_title}")
        print(f"视频ID: {video_id}\n")

        # 创建工作目录
        work_dir = os.path.join(output_dir, video_id)
        slices_dir = os.path.join(work_dir, 'slices')
        processed_dir = os.path.join(work_dir, 'processed')
        os.makedirs(slices_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)

        # 如果不是本地模式，创建数据库记录
        if not self.local_mode:
            video_info = self.video_slicer.get_video_info(input_video_path)
            self.video_dao.create_video(
                video_id=video_id,
                title=video_title,
                original_filename=video_title,
                duration=int(video_info['duration']),
                file_size=os.path.getsize(input_video_path)
            )

        # ============ 阶段1: 视频切片 ============
        print("\n📹 阶段1: 视频切片")
        slice_files = self.video_slicer.slice_video(input_video_path, slices_dir)
        print(f"✅ 切片完成: {len(slice_files)} 个切片\n")

        # ============ 阶段2: DLP扫描与脱敏 ============
        print("\n🔍 阶段2: DLP扫描与脱敏处理")
        processed_slices = []
        total_sensitive_count = 0
        all_detections = []  # 收集所有检测结果用于审计日志

        for slice_idx, slice_file in enumerate(slice_files):
            print(f"\n--- 处理切片 {slice_idx + 1}/{len(slice_files)}: {os.path.basename(slice_file)} ---")

            # 提取关键帧
            frames = self.video_slicer.extract_keyframes(slice_file, interval=1.0)

            # 扫描关键帧
            scan_results = self.dlp_scanner.scan_video_frames(frames)

            if not scan_results:
                print("  ✓ 未发现敏感信息，直接使用原切片")
                processed_slices.append(slice_file)
                continue

            # 发现敏感信息，需要处理视频
            print(f"  ⚠️  发现 {len(scan_results)} 帧包含敏感信息，开始脱敏...")

            # 创建敏感帧映射
            sensitive_frames = {result['frame_id']: result for result in scan_results}

            # 逐帧处理视频
            processed_slice_path = os.path.join(processed_dir, f"processed_{os.path.basename(slice_file)}")
            self._process_slice_video(slice_file, processed_slice_path, sensitive_frames)

            processed_slices.append(processed_slice_path)

            # 记录审计日志
            for result in scan_results:
                total_sensitive_count += result['scan_result']['sensitive_count']

                # 收集检测信息（本地模式和云端模式都需要）
                for detection in result['scan_result']['detections']:
                    bbox = detection['bbox']
                    detection_record = {
                        'slice_index': slice_idx,
                        'frame_id': result['frame_id'],
                        'timestamp': result['timestamp'],
                        'type': detection['sensitive_type'],
                        'text': detection['ocr_text'][:100],
                        'confidence': detection['ocr_confidence'],
                        'bbox': {
                            'x': bbox[0],
                            'y': bbox[1],
                            'width': bbox[2],
                            'height': bbox[3]
                        }
                    }
                    all_detections.append(detection_record)

                    # 如果不是本地模式，写入数据库
                    if not self.local_mode:
                        self.audit_dao.create_audit_log(
                            video_id=video_id,
                            slice_index=slice_idx,
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

        print(f"\n✅ DLP扫描完成: 共检测到 {total_sensitive_count} 个敏感信息\n")

        # 如果是本地模式，保存审计日志到文件
        if self.local_mode:
            audit_log_file = os.path.join(work_dir, 'audit_log.json')
            with open(audit_log_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'video_id': video_id,
                    'video_title': video_title,
                    'total_detections': total_sensitive_count,
                    'detections': all_detections,
                    'processed_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            print(f"📝 审计日志已保存: {audit_log_file}")

        # ============ 阶段3: 视频合并 ============
        print("\n🎞️  阶段3: 合并处理后的视频")
        final_output_path = os.path.join(output_dir, f"{video_id}_sanitized.mp4")
        success = self.video_merger.merge(processed_slices, final_output_path, use_ffmpeg=True)

        if success:
            print(f"✅ 处理完成!\n")
            print(f"输出文件: {final_output_path}")
            print(f"敏感信息检测: {total_sensitive_count} 个")

            # 如果不是本地模式，更新数据库
            if not self.local_mode:
                self.video_dao.update_video_status(video_id, 'completed', output_url=final_output_path)
                self.video_dao.update_sensitive_count(video_id, total_sensitive_count)

            return {
                'success': True,
                'video_id': video_id,
                'output_path': final_output_path,
                'sensitive_count': total_sensitive_count
            }
        else:
            print("❌ 视频合并失败")
            if not self.local_mode:
                self.video_dao.update_video_status(video_id, 'failed')

            return {
                'success': False,
                'video_id': video_id,
                'error': '视频合并失败'
            }

    def _process_slice_video(self, input_path, output_path, sensitive_frames):
        """
        处理单个切片视频，对敏感帧进行脱敏
        :param input_path: 输入视频路径
        :param output_path: 输出视频路径
        :param sensitive_frames: 敏感帧映射 {frame_id: scan_result}
        """
        cap = cv2.VideoCapture(input_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_id = 0
        interval_frames = int(fps * 1.0)  # 对应提取关键帧的间隔

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # 检查当前帧是否需要脱敏
            keyframe_id = frame_id // interval_frames
            if keyframe_id in sensitive_frames:
                result = sensitive_frames[keyframe_id]
                detections = result['scan_result']['detections']
                frame = self.masker.mask_frame(frame, detections, method='blur')

            out.write(frame)
            frame_id += 1

        cap.release()
        out.release()


def main():
    """主函数 - 本地测试入口"""
    print("\n" + "=" * 60)
    print("Video Vault - 本地测试模式")
    print("=" * 60 + "\n")

    # 检查测试视频
    test_video = './local_tests/test_video.mp4'
    if not os.path.exists(test_video):
        print(f"⚠️  测试视频不存在: {test_video}")
        print("\n请将测试视频放置到 ./local_tests/test_video.mp4")
        print("或者指定其他视频路径作为命令行参数:")
        print("  python local_test_pipeline.py <video_path>")
        return

    # 如果有命令行参数，使用指定的视频
    if len(sys.argv) > 1:
        test_video = sys.argv[1]

    if not os.path.exists(test_video):
        print(f"❌ 视频文件不存在: {test_video}")
        return

    # 创建处理流水线
    pipeline = VideoVaultPipeline(local_mode=True)

    # 处理视频
    result = pipeline.process_video(test_video)

    # 输出结果
    print("\n" + "=" * 60)
    if result['success']:
        print("✅ 处理成功!")
        print(f"视频ID: {result['video_id']}")
        print(f"输出路径: {result['output_path']}")
        print(f"检测到敏感信息: {result['sensitive_count']} 个")
    else:
        print("❌ 处理失败!")
        print(f"错误: {result.get('error', '未知错误')}")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
