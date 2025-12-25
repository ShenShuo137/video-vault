"""
AI Agent 工具集 - Serverless版本
从OBS读取数据，不依赖数据库
适用于完全Serverless架构
"""
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.obs_helper import OBSHelper
from shared.config import Config


class VideoVaultToolsServerless:
    """Video Vault AI Agent 工具集 - Serverless版本"""

    def __init__(self):
        """初始化OBS Helper"""
        self.obs_helper = OBSHelper()

    def _read_audit_log_from_obs(self, video_id):
        """从OBS读取单个视频的审计日志"""
        log_key = f"logs/{video_id}_audit.json"
        temp_file = f"/tmp/audit_{video_id}.json"

        try:
            # 下载审计日志
            success = self.obs_helper.download_file(log_key, temp_file)
            if not success or not os.path.exists(temp_file):
                return None

            # 读取JSON
            with open(temp_file, 'r', encoding='utf-8') as f:
                audit_data = json.load(f)

            # 清理临时文件
            os.remove(temp_file)

            return audit_data

        except Exception as e:
            print(f"读取审计日志失败 {video_id}: {str(e)}")
            return None

    def _list_all_audit_logs(self):
        """列出所有审计日志"""
        all_logs = []

        try:
            # 列出logs/目录下的所有文件
            log_files = self.obs_helper.list_objects(prefix='logs/')

            for log_key in log_files:
                if not log_key.endswith('_audit.json'):
                    continue

                # 提取video_id
                video_id = log_key.replace('logs/', '').replace('_audit.json', '')

                # 读取审计日志
                audit_data = self._read_audit_log_from_obs(video_id)
                if audit_data and 'detections' in audit_data:
                    # 为每条检测记录添加video_id
                    for detection in audit_data['detections']:
                        detection['video_id'] = video_id
                        detection['video_title'] = audit_data.get('video_title', video_id)
                        # 统一字段名
                        if 'type' in detection:
                            detection['sensitive_type'] = detection['type']
                        if 'text' in detection:
                            detection['detected_text'] = detection['text']

                    all_logs.extend(audit_data['detections'])

        except Exception as e:
            print(f"列出审计日志失败: {str(e)}")

        return all_logs

    def _list_all_videos(self):
        """列出所有处理完成的视频"""
        videos = []

        try:
            # 列出outputs/目录下的所有文件
            output_files = self.obs_helper.list_objects(prefix='outputs/')

            for output_key in output_files:
                if not output_key.endswith('_sanitized.mp4'):
                    continue

                # 提取video_id
                video_id = output_key.replace('outputs/', '').replace('_sanitized.mp4', '')

                # 读取审计日志获取详细信息
                audit_data = self._read_audit_log_from_obs(video_id)

                video_info = {
                    'video_id': video_id,
                    'filename': f"{video_id}_sanitized.mp4",
                    'status': 'completed',
                    'sensitive_count': 0
                }

                if audit_data:
                    video_info['title'] = audit_data.get('video_title', video_id)
                    video_info['sensitive_count'] = audit_data.get('total_detections', 0)

                videos.append(video_info)

        except Exception as e:
            print(f"列出视频失败: {str(e)}")

        return videos

    def query_audit_logs(self, video_id=None, days=7, sensitive_type=None):
        """
        查询审计日志
        :param video_id: 视频ID(可选)
        :param days: 查询最近几天的日志（Serverless模式忽略此参数）
        :param sensitive_type: 敏感信息类型(可选)
        :return: 审计日志列表
        """
        try:
            if video_id:
                # 查询单个视频的审计日志
                audit_data = self._read_audit_log_from_obs(video_id)
                if not audit_data:
                    return {
                        'total_count': 0,
                        'logs': [],
                        'summary': f'未找到视频 {video_id} 的审计日志'
                    }

                logs = audit_data.get('detections', [])
                # 统一字段名
                for log in logs:
                    log['video_id'] = video_id
                    log['video_title'] = audit_data.get('video_title', video_id)
                    if 'type' in log:
                        log['sensitive_type'] = log['type']
                    if 'text' in log:
                        log['detected_text'] = log['text']

            else:
                # 查询所有视频的审计日志
                logs = self._list_all_audit_logs()

            # 如果指定了敏感信息类型，进行过滤
            if sensitive_type:
                logs = [log for log in logs if log.get('sensitive_type') == sensitive_type or log.get('type') == sensitive_type]

            # 格式化结果
            result = {
                'total_count': len(logs),
                'logs': logs[:20],  # 限制返回数量
                'summary': self._summarize_audit_logs(logs)
            }

            return result

        except Exception as e:
            return {'error': str(e)}

    def get_video_status(self, video_id):
        """
        查询视频处理状态
        :param video_id: 视频ID
        :return: 视频信息
        """
        try:
            # 读取审计日志
            audit_data = self._read_audit_log_from_obs(video_id)

            if not audit_data:
                return {'error': f'视频不存在或尚未处理完成: {video_id}'}

            # 统计各类敏感信息数量
            type_stats = {}
            for detection in audit_data.get('detections', []):
                t = detection.get('type', 'unknown')
                type_stats[t] = type_stats.get(t, 0) + 1

            result = {
                'video_info': {
                    'video_id': video_id,
                    'title': audit_data.get('video_title', video_id),
                    'status': 'completed',
                    'sensitive_count': audit_data.get('total_detections', 0)
                },
                'sensitive_stats': type_stats,
                'status_description': '处理完成'
            }

            return result

        except Exception as e:
            return {'error': str(e)}

    def list_sensitive_videos(self, threshold=5, limit=20):
        """
        列出高风险视频(敏感信息数量超过阈值)
        :param threshold: 敏感信息数量阈值
        :param limit: 返回数量限制
        :return: 高风险视频列表
        """
        try:
            # 获取所有视频
            videos = self._list_all_videos()

            # 过滤出高风险视频
            high_risk_videos = [
                v for v in videos
                if v.get('sensitive_count', 0) >= threshold
            ]

            # 按敏感信息数量降序排序
            high_risk_videos.sort(key=lambda x: x.get('sensitive_count', 0), reverse=True)

            result = {
                'total_count': len(high_risk_videos),
                'threshold': threshold,
                'videos': high_risk_videos[:limit]
            }

            return result

        except Exception as e:
            return {'error': str(e)}

    def extract_watermark(self, watermark_id):
        """
        提取水印信息(查询水印对应的用户)
        :param watermark_id: 水印ID
        :return: 用户信息
        """
        # Serverless架构下，水印功能暂未实现
        return {
            'watermark_id': watermark_id,
            'mock': True,
            'trace_result': '水印提取功能尚未启用(预留功能)'
        }

    def get_security_report(self, days=7):
        """
        生成安全报告
        :param days: 统计最近几天（Serverless模式忽略此参数）
        :return: 安全报告
        """
        try:
            # 获取所有审计日志
            logs = self._list_all_audit_logs()

            # 获取所有视频
            videos = self._list_all_videos()

            # 统计各类敏感信息数量
            type_stats = {}
            for log in logs:
                t = log.get('sensitive_type') or log.get('type', 'unknown')
                type_stats[t] = type_stats.get(t, 0) + 1

            # 获取高风险视频
            high_risk = self.list_sensitive_videos(threshold=5)

            report = {
                'period': '全部数据（Serverless模式）',
                'total_videos_processed': len(videos),
                'total_sensitive_detected': len(logs),
                'sensitive_by_type': type_stats,
                'high_risk_videos_count': high_risk['total_count'],
                'top_high_risk_videos': high_risk['videos'][:5]
            }

            return report

        except Exception as e:
            return {'error': str(e)}

    def _summarize_audit_logs(self, logs):
        """汇总审计日志"""
        if not logs:
            return '未发现敏感信息'

        # 统计各类型数量
        type_counts = {}
        for log in logs:
            t = log.get('sensitive_type') or log.get('type', 'unknown')
            type_counts[t] = type_counts.get(t, 0) + 1

        summary = ', '.join([f'{k}: {v}次' for k, v in type_counts.items()])
        return f'共检测到 {len(logs)} 次敏感信息暴露 ({summary})'


# 工具函数的schema保持不变（与原tools.py相同）
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "query_audit_logs",
            "description": "查询视频安全审计日志，可以查看某个视频或所有视频检测到的敏感信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "视频ID(可选)，如果指定则只查询该视频的日志"
                    },
                    "days": {
                        "type": "integer",
                        "description": "查询最近几天的日志（Serverless模式下忽略此参数）",
                        "default": 7
                    },
                    "sensitive_type": {
                        "type": "string",
                        "description": "敏感信息类型(可选): openai_key, aws_key, password, id_card, phone等"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_video_status",
            "description": "查询指定视频的处理状态和敏感信息统计",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "视频ID"
                    }
                },
                "required": ["video_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_sensitive_videos",
            "description": "列出包含大量敏感信息的高风险视频",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "integer",
                        "description": "敏感信息数量阈值，默认5",
                        "default": 5
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制，默认20",
                        "default": 20
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "extract_watermark",
            "description": "从泄露的视频中提取水印，追溯下载者身份（预留功能）",
            "parameters": {
                "type": "object",
                "properties": {
                    "watermark_id": {
                        "type": "string",
                        "description": "水印ID"
                    }
                },
                "required": ["watermark_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_security_report",
            "description": "生成安全报告，统计敏感信息检测情况",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "统计最近几天（Serverless模式下忽略此参数）",
                        "default": 7
                    }
                }
            }
        }
    }
]
