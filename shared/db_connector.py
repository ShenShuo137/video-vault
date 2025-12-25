"""
数据库连接模块
提供数据库连接和常用操作
"""
import pymysql
from contextlib import contextmanager
from shared.config import Config


class DatabaseConnector:
    """数据库连接器"""

    def __init__(self):
        self.config = {
            'host': Config.DB_HOST,
            'port': Config.DB_PORT,
            'user': Config.DB_USER,
            'password': Config.DB_PASSWORD,
            'database': Config.DB_NAME,
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }

    @contextmanager
    def get_connection(self):
        """获取数据库连接(上下文管理器)"""
        conn = None
        try:
            conn = pymysql.connect(**self.config)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def execute_query(self, sql, params=None):
        """执行查询并返回结果"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()

    def execute_insert(self, sql, params=None):
        """执行插入并返回插入的ID"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.lastrowid

    def execute_update(self, sql, params=None):
        """执行更新并返回影响的行数"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                return cursor.execute(sql, params or ())


# 视频相关数据库操作
class VideoDAO:
    """视频数据访问对象"""

    def __init__(self):
        self.db = DatabaseConnector()

    def create_video(self, video_id, title, original_filename, duration=None, file_size=None, obs_input_path=None):
        """创建视频记录"""
        sql = """
        INSERT INTO videos (video_id, title, original_filename, duration, file_size, obs_input_path, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'uploading')
        """
        return self.db.execute_insert(sql, (video_id, title, original_filename, duration, file_size, obs_input_path))

    def update_video_status(self, video_id, status, obs_output_path=None, output_url=None):
        """更新视频处理状态"""
        sql = """
        UPDATE videos
        SET status = %s, obs_output_path = %s, output_url = %s, updated_at = NOW()
        WHERE video_id = %s
        """
        return self.db.execute_update(sql, (status, obs_output_path, output_url, video_id))

    def update_sensitive_count(self, video_id, count):
        """更新敏感信息数量"""
        sql = "UPDATE videos SET sensitive_count = %s WHERE video_id = %s"
        return self.db.execute_update(sql, (count, video_id))

    def get_video_by_id(self, video_id):
        """根据ID获取视频信息"""
        sql = "SELECT * FROM videos WHERE video_id = %s"
        results = self.db.execute_query(sql, (video_id,))
        return results[0] if results else None

    def list_videos(self, status=None, limit=50):
        """列出视频"""
        if status:
            sql = "SELECT * FROM videos WHERE status = %s ORDER BY upload_time DESC LIMIT %s"
            return self.db.execute_query(sql, (status, limit))
        else:
            sql = "SELECT * FROM videos ORDER BY upload_time DESC LIMIT %s"
            return self.db.execute_query(sql, (limit,))


# 审计日志相关操作
class AuditLogDAO:
    """审计日志数据访问对象"""

    def __init__(self):
        self.db = DatabaseConnector()

    def create_audit_log(self, video_id, slice_index, frame_id, timestamp_in_video,
                        sensitive_type, detected_text=None, confidence=None,
                        bbox_x=None, bbox_y=None, bbox_width=None, bbox_height=None):
        """创建审计日志"""
        sql = """
        INSERT INTO audit_logs
        (video_id, slice_index, frame_id, timestamp_in_video, sensitive_type,
         detected_text, confidence, bbox_x, bbox_y, bbox_width, bbox_height)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.db.execute_insert(sql, (
            video_id, slice_index, frame_id, timestamp_in_video, sensitive_type,
            detected_text, confidence, bbox_x, bbox_y, bbox_width, bbox_height
        ))

    def get_audit_logs_by_video(self, video_id):
        """获取视频的所有审计日志"""
        sql = """
        SELECT * FROM audit_logs
        WHERE video_id = %s
        ORDER BY timestamp_in_video ASC
        """
        return self.db.execute_query(sql, (video_id,))

    def count_sensitive_by_type(self, video_id):
        """统计视频中各类敏感信息的数量"""
        sql = """
        SELECT sensitive_type, COUNT(*) as count
        FROM audit_logs
        WHERE video_id = %s
        GROUP BY sensitive_type
        """
        return self.db.execute_query(sql, (video_id,))

    def get_recent_audit_logs(self, days=7, limit=100):
        """获取最近的审计日志"""
        sql = """
        SELECT a.*, v.title as video_title
        FROM audit_logs a
        LEFT JOIN videos v ON a.video_id = v.video_id
        WHERE a.detected_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
        ORDER BY a.detected_time DESC
        LIMIT %s
        """
        return self.db.execute_query(sql, (days, limit))


# 水印溯源相关操作 (预留)
class WatermarkDAO:
    """水印数据访问对象"""

    def __init__(self):
        self.db = DatabaseConnector()

    def create_watermark_mapping(self, watermark_id, video_id, user_id, user_name,
                                 user_email=None, department=None, download_ip=None):
        """创建水印映射记录"""
        sql = """
        INSERT INTO watermark_mapping
        (watermark_id, video_id, user_id, user_name, user_email, department, download_ip)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        return self.db.execute_insert(sql, (
            watermark_id, video_id, user_id, user_name, user_email, department, download_ip
        ))

    def get_user_by_watermark(self, watermark_id):
        """根据水印ID查找用户"""
        sql = "SELECT * FROM watermark_mapping WHERE watermark_id = %s"
        results = self.db.execute_query(sql, (watermark_id,))
        return results[0] if results else None
