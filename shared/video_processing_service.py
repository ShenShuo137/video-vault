"""
视频处理服务抽象层
支持本地FFmpeg和华为云MPC(Media Processing Center)无缝切换
"""
import os
import subprocess
import cv2
from shared.config import Config


class VideoProcessingService:
    """视频处理服务 - 自动选择本地或云端"""

    def __init__(self):
        self.use_cloud = not Config.LOCAL_MODE
        print(f"视频处理模式: {'华为云MPC' if self.use_cloud else '本地FFmpeg'}")

    def merge_videos(self, slice_files, output_path):
        """
        合并视频切片
        :param slice_files: 切片文件路径列表(按顺序)
        :param output_path: 输出文件路径
        :return: 是否成功
        """
        if self.use_cloud:
            return self._huawei_mpc_merge(slice_files, output_path)
        else:
            return self._local_merge(slice_files, output_path)

    def _local_merge(self, slice_files, output_path):
        """本地FFmpeg/OpenCV合并"""
        if not slice_files:
            print("没有切片文件需要合并")
            return False

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 优先尝试FFmpeg
        if self._check_ffmpeg():
            return self._merge_with_ffmpeg(slice_files, output_path)
        else:
            print("FFmpeg不可用，使用OpenCV合并")
            return self._merge_with_opencv(slice_files, output_path)

    def _check_ffmpeg(self):
        """检查FFmpeg是否可用"""
        try:
            subprocess.run(['ffmpeg', '-version'],
                          capture_output=True,
                          check=True,
                          timeout=5)
            return True
        except:
            return False

    def _merge_with_ffmpeg(self, slice_files, output_path):
        """使用FFmpeg合并"""
        try:
            print(f"使用FFmpeg合并 {len(slice_files)} 个切片...")

            # 创建临时文件列表
            list_file = output_path + '.list.txt'
            with open(list_file, 'w', encoding='utf-8') as f:
                for slice_file in slice_files:
                    abs_path = os.path.abspath(slice_file).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")

            # FFmpeg合并命令
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', list_file,
                '-c', 'copy',
                output_path,
                '-y'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                print(f"合并完成: {output_path}")
                os.remove(list_file)
                return True
            else:
                print(f"FFmpeg错误: {result.stderr}")
                return False

        except Exception as e:
            print(f"FFmpeg合并异常: {str(e)}")
            return False

    def _merge_with_opencv(self, slice_files, output_path):
        """使用OpenCV合并"""
        try:
            print(f"使用OpenCV合并 {len(slice_files)} 个切片...")

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

        except Exception as e:
            print(f"OpenCV合并异常: {str(e)}")
            return False

    def _huawei_mpc_merge(self, slice_files, output_path):
        """
        使用华为云MPC服务合并视频
        通过视频拼接任务实现
        """
        try:
            from shared.obs_helper import OBSHelper
            from huaweicloudsdkcore.auth.credentials import BasicCredentials
            from huaweicloudsdkmpc.v1.region.mpc_region import MpcRegion
            from huaweicloudsdkmpc.v1 import (
                MpcClient,
                CreateMergeChannelsTaskRequest,
                MergeChannelsTaskInfo,
                ObsObjInfo,
                MergeSourceInfo,
                ShowMergeChannelsTaskRequest
            )
            import time
            import uuid

            print(f"使用华为云MPC合并 {len(slice_files)} 个切片...")

            obs_helper = OBSHelper()
            task_id = str(uuid.uuid4())

            # Step 1: 上传所有切片到OBS
            print("Step 1: 上传切片到OBS...")
            obs_slice_keys = []
            for i, local_file in enumerate(slice_files):
                obs_key = f"temp/slices/{task_id}/slice_{i:04d}.mp4"
                success = obs_helper.upload_file(local_file, obs_key)
                if success:
                    obs_slice_keys.append(obs_key)
                    print(f"  上传切片 {i+1}/{len(slice_files)}: {obs_key}")
                else:
                    raise Exception(f"上传切片失败: {local_file}")

            # Step 2: 初始化MPC客户端
            credentials = BasicCredentials(Config.HUAWEI_CLOUD_AK, Config.HUAWEI_CLOUD_SK)
            client = MpcClient.new_builder() \
                .with_credentials(credentials) \
                .with_region(MpcRegion.value_of(Config.HUAWEI_CLOUD_REGION)) \
                .build()

            # Step 3: 创建视频拼接任务
            print("Step 2: 创建MPC拼接任务...")
            output_obs_key = f"temp/output/{task_id}/merged.mp4"

            request = CreateMergeChannelsTaskRequest()

            # 构建拼接源列表
            sources = []
            for obs_key in obs_slice_keys:
                source = MergeSourceInfo(
                    source=ObsObjInfo(
                        bucket=Config.OBS_BUCKET_NAME,
                        location=Config.HUAWEI_CLOUD_REGION,
                        object=obs_key
                    )
                )
                sources.append(source)

            # 构建任务信息
            request.body = MergeChannelsTaskInfo(
                output=ObsObjInfo(
                    bucket=Config.OBS_BUCKET_NAME,
                    location=Config.HUAWEI_CLOUD_REGION,
                    object=output_obs_key
                ),
                sources=sources
            )

            # 提交任务
            response = client.create_merge_channels_task(request)
            merge_task_id = response.task_id
            print(f"  任务已创建，ID: {merge_task_id}")

            # Step 4: 等待任务完成
            print("Step 3: 等待任务完成...")
            max_wait = 600  # 最多等待10分钟
            waited = 0

            while waited < max_wait:
                show_request = ShowMergeChannelsTaskRequest()
                show_request.task_id = merge_task_id

                task_status = client.show_merge_channels_task(show_request)

                if task_status.status == 'SUCCEED':
                    print("  ✓ 任务完成!")
                    break
                elif task_status.status == 'FAILED':
                    error_msg = getattr(task_status, 'error_msg', '未知错误')
                    raise Exception(f"MPC任务失败: {error_msg}")
                elif task_status.status in ['PROCESSING', 'WAITING']:
                    print(f"  处理中... (已等待 {waited}秒)")
                    time.sleep(10)
                    waited += 10
                else:
                    print(f"  未知状态: {task_status.status}")
                    time.sleep(5)
                    waited += 5

            if waited >= max_wait:
                raise Exception("任务超时")

            # Step 5: 下载合并后的视频
            print("Step 4: 下载结果...")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            success = obs_helper.download_file(output_obs_key, output_path)

            if not success:
                raise Exception("下载合并后视频失败")

            # Step 6: 清理临时文件
            print("Step 5: 清理临时文件...")
            for obs_key in obs_slice_keys:
                obs_helper.delete_object(obs_key)
            obs_helper.delete_object(output_obs_key)

            print(f"✓ MPC合并完成: {output_path}")
            return True

        except ImportError as e:
            print(f"华为云MPC SDK未安装: {e}")
            print("请安装: pip install huaweicloudsdkmpc")
            print("降级使用本地FFmpeg/OpenCV")
            return self._local_merge(slice_files, output_path)

        except Exception as e:
            print(f"华为云MPC错误: {str(e)}")
            print("降级使用本地FFmpeg/OpenCV")
            return self._local_merge(slice_files, output_path)
