"""
OBS对象存储帮助模块
封装华为云OBS操作
"""
import os
from obs import ObsClient
from shared.config import Config


class OBSHelper:
    """华为云OBS操作封装"""

    def __init__(self):
        self.bucket_name = Config.OBS_BUCKET_NAME
        if Config.LOCAL_MODE:
            self.client = None
            print("运行在本地模式，OBS客户端未初始化")
        else:
            self.client = ObsClient(
                access_key_id=Config.HUAWEI_CLOUD_AK,
                secret_access_key=Config.HUAWEI_CLOUD_SK,
                server=Config.OBS_ENDPOINT
            )

    def upload_file(self, local_file_path, obs_key):
        """上传文件到OBS"""
        if Config.LOCAL_MODE:
            print(f"[本地模式] 模拟上传: {local_file_path} -> {obs_key}")
            return True

        try:
            resp = self.client.putFile(self.bucket_name, obs_key, local_file_path)
            if resp.status < 300:
                print(f"上传成功: {obs_key}")
                return True
            else:
                print(f"上传失败: {resp.errorCode} - {resp.errorMessage}")
                return False
        except Exception as e:
            print(f"上传异常: {str(e)}")
            return False

    def download_file(self, obs_key, local_file_path):
        """从OBS下载文件"""
        if Config.LOCAL_MODE:
            print(f"[本地模式] 模拟下载: {obs_key} -> {local_file_path}")
            return True

        try:
            # 确保目标目录存在
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

            resp = self.client.getObject(self.bucket_name, obs_key, downloadPath=local_file_path)
            if resp.status < 300:
                print(f"下载成功: {obs_key}")
                return True
            else:
                print(f"下载失败: {resp.errorCode} - {resp.errorMessage}")
                return False
        except Exception as e:
            print(f"下载异常: {str(e)}")
            return False

    def list_objects(self, prefix=''):
        """列出OBS中的对象"""
        if Config.LOCAL_MODE:
            print(f"[本地模式] 模拟列出对象: {prefix}")
            return []

        try:
            resp = self.client.listObjects(self.bucket_name, prefix=prefix)
            if resp.status < 300:
                return [obj.key for obj in resp.body.contents]
            else:
                print(f"列表失败: {resp.errorCode} - {resp.errorMessage}")
                return []
        except Exception as e:
            print(f"列表异常: {str(e)}")
            return []

    def delete_object(self, obs_key):
        """删除OBS中的对象"""
        if Config.LOCAL_MODE:
            print(f"[本地模式] 模拟删除: {obs_key}")
            return True

        try:
            resp = self.client.deleteObject(self.bucket_name, obs_key)
            if resp.status < 300:
                print(f"删除成功: {obs_key}")
                return True
            else:
                print(f"删除失败: {resp.errorCode} - {resp.errorMessage}")
                return False
        except Exception as e:
            print(f"删除异常: {str(e)}")
            return False

    def get_download_url(self, obs_key, expires=3600):
        """生成下载URL(签名URL)"""
        if Config.LOCAL_MODE:
            return f"file://{obs_key}"

        try:
            resp = self.client.createSignedUrl(
                'GET',
                self.bucket_name,
                obs_key,
                expires
            )
            return resp.signedUrl
        except Exception as e:
            print(f"生成URL异常: {str(e)}")
            return None

    def close(self):
        """关闭OBS客户端"""
        if self.client:
            self.client.close()
