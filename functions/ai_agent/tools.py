"""
AI Agent 工具集
提供查询数据库和系统状态的工具函数
支持本地模式（从文件系统读取）和云端模式（从数据库读取）
"""
import sys
import os
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.db_connector import VideoDAO, AuditLogDAO, WatermarkDAO
from shared.config import Config
from datetime import datetime, timedelta


class VideoVaultTools:
    """Video Vault AI Agent 工具集"""

    def __init__(self):
        """初始化数据访问对象"""
        self.local_mode = Config.LOCAL_MODE

        if not self.local_mode:
            self.video_dao = VideoDAO()
            self.audit_dao = AuditLogDAO()
            self.watermark_dao = WatermarkDAO()
        else:
            # 本地模式：设置文件路径
            self.uploads_dir = os.path.join(os.path.dirname(__file__), '../../backend/uploads')
            self.output_dir = os.path.join(self.uploads_dir, 'output')

    def _read_local_audit_logs(self):
        """从本地文件系统读取所有审计日志"""
        all_logs = []

        if not os.path.exists(self.output_dir):
            return all_logs

        video_files = [f for f in os.listdir(self.output_dir) if f.endswith('_sanitized.mp4')]

        for video_file in video_files:
            video_id = video_file.replace('_sanitized.mp4', '')
            video_dir = os.path.join(self.output_dir, video_id)
            audit_file = os.path.join(video_dir, 'audit_log.json')

            if os.path.exists(audit_file):
                try:
                    with open(audit_file, 'r', encoding='utf-8') as f:
                        audit_data = json.load(f)
                        detections = audit_data.get('detections', [])

                        # 为每条记录添加video_id和video_title
                        for detection in detections:
                            detection['video_id'] = video_id
                            detection['video_title'] = audit_data.get('video_title', video_id)
                            detection['sensitive_type'] = detection.get('type', 'unknown')
                            detection['detected_text'] = detection.get('text', '')

                        all_logs.extend(detections)
                except Exception as e:
                    print(f"读取审计日志失败: {audit_file}, 错误: {e}")

        return all_logs

    def _read_local_videos(self):
        """从本地文件系统读取所有视频信息"""
        videos = []

        if not os.path.exists(self.output_dir):
            return videos

        video_files = [f for f in os.listdir(self.output_dir) if f.endswith('_sanitized.mp4')]

        for video_file in video_files:
            video_id = video_file.replace('_sanitized.mp4', '')
            video_dir = os.path.join(self.output_dir, video_id)
            audit_file = os.path.join(video_dir, 'audit_log.json')

            video_info = {
                'video_id': video_id,
                'filename': video_file,
                'status': 'completed',
                'sensitive_count': 0
            }

            if os.path.exists(audit_file):
                try:
                    with open(audit_file, 'r', encoding='utf-8') as f:
                        audit_data = json.load(f)
                        video_info['title'] = audit_data.get('video_title', video_id)
                        video_info['sensitive_count'] = audit_data.get('total_detections', 0)
                except:
                    pass

            videos.append(video_info)

        return videos

    def query_audit_logs(self, video_id=None, days=7, sensitive_type=None):
        """
        查询审计日志
        :param video_id: 视频ID(可选)
        :param days: 查询最近几天的日志
        :param sensitive_type: 敏感信息类型(可选)
        :return: 审计日志列表
        """
        try:
            if self.local_mode:
                # 本地模式：从文件系统读取
                logs = self._read_local_audit_logs()

                # 如果指定了video_id，进行过滤
                if video_id:
                    logs = [log for log in logs if log.get('video_id') == video_id]

            else:
                # 云端模式：从数据库读取
                if video_id:
                    logs = self.audit_dao.get_audit_logs_by_video(video_id)
                else:
                    logs = self.audit_dao.get_recent_audit_logs(days=days)

            # 如果指定了敏感信息类型，进行过滤
            if sensitive_type:
                logs = [log for log in logs if log.get('sensitive_type') == sensitive_type]

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
            if self.local_mode:
                # 本地模式：从文件系统读取
                video_dir = os.path.join(self.output_dir, video_id)
                audit_file = os.path.join(video_dir, 'audit_log.json')

                if not os.path.exists(audit_file):
                    return {'error': f'视频不存在: {video_id}'}

                with open(audit_file, 'r', encoding='utf-8') as f:
                    audit_data = json.load(f)

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

            else:
                # 云端模式：从数据库读取
                video = self.video_dao.get_video_by_id(video_id)

                if not video:
                    return {'error': f'视频不存在: {video_id}'}

                # 获取该视频的审计统计
                audit_stats = self.audit_dao.count_sensitive_by_type(video_id)

                result = {
                    'video_info': video,
                    'sensitive_stats': audit_stats,
                    'status_description': self._get_status_description(video['status'])
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
            if self.local_mode:
                # 本地模式：从文件系统读取
                videos = self._read_local_videos()
            else:
                # 云端模式：从数据库读取
                videos = self.video_dao.list_videos(status='completed', limit=100)

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
        try:
            mapping = self.watermark_dao.get_user_by_watermark(watermark_id)

            if not mapping:
                return {'error': f'未找到水印记录: {watermark_id}'}

            result = {
                'watermark_id': watermark_id,
                'user_info': mapping,
                'trace_result': f"该视频由 {mapping['user_name']} 于 {mapping['download_time']} 下载"
            }

            return result

        except Exception as e:
            # 如果是本地模式或水印功能未启用，返回模拟数据
            return {
                'watermark_id': watermark_id,
                'mock': True,
                'trace_result': '水印提取功能尚未启用(预留功能)'
            }

    def get_security_report(self, days=7):
        """
        生成安全报告
        :param days: 统计最近几天
        :return: 安全报告
        """
        try:
            if self.local_mode:
                # 本地模式：从文件系统读取
                logs = self._read_local_audit_logs()
                videos = self._read_local_videos()
                completed_videos = videos  # 本地模式下都是已完成的

                # 统计各类敏感信息数量
                type_stats = {}
                for log in logs:
                    t = log.get('sensitive_type', 'unknown')
                    type_stats[t] = type_stats.get(t, 0) + 1

                # 获取高风险视频
                high_risk = self.list_sensitive_videos(threshold=5)

            else:
                # 云端模式：从数据库读取
                logs = self.audit_dao.get_recent_audit_logs(days=days)

                # 统计各类敏感信息数量
                type_stats = {}
                for log in logs:
                    t = log['sensitive_type']
                    type_stats[t] = type_stats.get(t, 0) + 1

                # 获取处理的视频数量
                videos = self.video_dao.list_videos(limit=1000)
                completed_videos = [v for v in videos if v['status'] == 'completed']

                # 获取高风险视频
                high_risk = self.list_sensitive_videos(threshold=5)

            report = {
                'period': f'最近{days}天' if not self.local_mode else '全部数据',
                'total_videos_processed': len(completed_videos),
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
            t = log['sensitive_type']
            type_counts[t] = type_counts.get(t, 0) + 1

        summary = ', '.join([f'{k}: {v}次' for k, v in type_counts.items()])
        return f'共检测到 {len(logs)} 次敏感信息暴露 ({summary})'

    def _get_status_description(self, status):
        """获取状态描述"""
        status_map = {
            'uploading': '正在上传',
            'processing': '正在处理',
            'completed': '处理完成',
            'failed': '处理失败'
        }
        return status_map.get(status, '未知状态')


# 定义工具函数的schema (用于OpenAI Function Calling)
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "query_audit_logs",
            "description": "查询视频安全审计日志，可以查看某个视频或最近几天内检测到的敏感信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "video_id": {
                        "type": "string",
                        "description": "视频ID(可选)，如果指定则只查询该视频的日志"
                    },
                    "days": {
                        "type": "integer",
                        "description": "查询最近几天的日志，默认7天",
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
            "description": "从泄露的视频中提取水印，追溯下载者身份",
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
            "description": "生成安全报告，统计最近的敏感信息检测情况",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "统计最近几天，默认7天",
                        "default": 7
                    }
                }
            }
        }
    }
]
