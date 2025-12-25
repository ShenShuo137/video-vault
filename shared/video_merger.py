"""
视频合并模块
使用FFmpeg或OpenCV合并处理后的视频切片
支持本地和云端模式
"""
import os
import subprocess
import cv2
from shared.video_processing_service import VideoProcessingService


class VideoMerger:
    """视频合并器"""

    def __init__(self):
        self.video_service = VideoProcessingService()  # 使用视频处理服务抽象层

    def merge_with_opencv(self, slice_files, output_path):
        """
        使用OpenCV合并视频切片
        :param slice_files: 切片文件路径列表(按顺序)
        :param output_path: 输出文件路径
        :return: 是否成功
        """
        if not slice_files:
            print("没有切片文件需要合并")
            return False

        print(f"开始合并 {len(slice_files)} 个切片...")

        # 读取第一个切片获取视频参数
        first_video = cv2.VideoCapture(slice_files[0])
        fps = first_video.get(cv2.CAP_PROP_FPS)
        width = int(first_video.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(first_video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        first_video.release()

        # 创建视频写入器
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # 逐个读取并写入切片
        for i, slice_file in enumerate(slice_files):
            print(f"处理切片 {i + 1}/{len(slice_files)}: {os.path.basename(slice_file)}")

            cap = cv2.VideoCapture(slice_file)
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
            cap.release()

        out.release()
        print(f"合并完成: {output_path}")
        return True

    def merge_with_ffmpeg(self, slice_files, output_path):
        """
        使用FFmpeg合并视频切片(更高效，推荐用于生产环境)
        :param slice_files: 切片文件路径列表(按顺序)
        :param output_path: 输出文件路径
        :return: 是否成功
        """
        if not slice_files:
            print("没有切片文件需要合并")
            return False

        # 创建临时文件列表
        list_file = output_path + '.list.txt'
        with open(list_file, 'w') as f:
            for slice_file in slice_files:
                # FFmpeg需要使用相对路径或绝对路径
                abs_path = os.path.abspath(slice_file)
                f.write(f"file '{abs_path}'\n")

        # 使用FFmpeg合并
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            output_path,
            '-y'  # 覆盖输出文件
        ]

        try:
            print(f"使用FFmpeg合并 {len(slice_files)} 个切片...")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"合并完成: {output_path}")
                os.remove(list_file)
                return True
            else:
                print(f"FFmpeg错误: {result.stderr}")
                return False

        except FileNotFoundError:
            print("未找到FFmpeg，请确保已安装FFmpeg并添加到PATH")
            print("降级使用OpenCV合并...")
            return self.merge_with_opencv(slice_files, output_path)

        except Exception as e:
            print(f"合并异常: {str(e)}")
            return False

    def merge(self, slice_files, output_path, use_ffmpeg=True):
        """
        合并视频切片
        :param slice_files: 切片文件路径列表(按顺序)
        :param output_path: 输出文件路径
        :param use_ffmpeg: 是否优先使用FFmpeg
        :return: 是否成功
        """
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if use_ffmpeg:
            return self.merge_with_ffmpeg(slice_files, output_path)
        else:
            return self.merge_with_opencv(slice_files, output_path)
