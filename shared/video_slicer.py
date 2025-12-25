"""
视频切片处理模块
将长视频切分成多个短片段
"""
import os
import cv2
from datetime import timedelta


class VideoSlicer:
    """视频切片器"""

    def __init__(self, slice_duration=60):
        """
        初始化
        :param slice_duration: 每个切片的时长(秒)，默认60秒
        """
        self.slice_duration = slice_duration

    def get_video_info(self, video_path):
        """获取视频信息"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"无法打开视频文件: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0

        cap.release()

        return {
            'fps': fps,
            'frame_count': frame_count,
            'width': width,
            'height': height,
            'duration': duration
        }

    def slice_video(self, input_video_path, output_dir):
        """
        切片视频
        :param input_video_path: 输入视频路径
        :param output_dir: 输出目录
        :return: 切片文件列表
        """
        os.makedirs(output_dir, exist_ok=True)

        video_info = self.get_video_info(input_video_path)
        print(f"视频信息: {video_info}")

        cap = cv2.VideoCapture(input_video_path)
        fps = video_info['fps']
        width = video_info['width']
        height = video_info['height']
        total_duration = video_info['duration']

        # 计算需要切分的片段数
        num_slices = int(total_duration / self.slice_duration) + 1
        print(f"将切分为 {num_slices} 个片段")

        slice_files = []
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        for slice_idx in range(num_slices):
            start_time = slice_idx * self.slice_duration
            end_time = min((slice_idx + 1) * self.slice_duration, total_duration)

            # 跳过最后一个可能过短的片段
            if end_time - start_time < 1:
                continue

            slice_filename = f"slice_{slice_idx:04d}.mp4"
            slice_path = os.path.join(output_dir, slice_filename)

            # 设置视频起始帧
            start_frame = int(start_time * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

            # 创建视频写入器
            out = cv2.VideoWriter(slice_path, fourcc, fps, (width, height))

            frames_to_read = int((end_time - start_time) * fps)
            frames_read = 0

            while frames_read < frames_to_read:
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
                frames_read += 1

            out.release()
            slice_files.append(slice_path)
            print(f"已创建切片: {slice_filename} ({start_time:.1f}s - {end_time:.1f}s)")

        cap.release()
        print(f"切片完成，共生成 {len(slice_files)} 个文件")
        return slice_files

    def extract_keyframes(self, video_path, interval=1.0):
        """
        提取关键帧
        :param video_path: 视频路径
        :param interval: 提取间隔(秒)，默认每秒1帧
        :return: 帧列表 [(frame_id, timestamp, frame_image), ...]
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception(f"无法打开视频文件: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * interval)

        frames = []
        frame_id = 0
        count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if count % frame_interval == 0:
                timestamp = count / fps
                frames.append((frame_id, timestamp, frame))
                frame_id += 1

            count += 1

        cap.release()
        print(f"提取了 {len(frames)} 个关键帧 (间隔={interval}秒)")
        return frames
