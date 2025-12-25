"""
Video Vault Flask 后端API
提供RESTful API接口
"""
import os
import sys
import uuid
import json
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.config import Config
from shared.db_connector import VideoDAO, AuditLogDAO
from local_tests.local_test_pipeline import VideoVaultPipeline
from functions.ai_agent.agent import VideoVaultAgent

# 初始化Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB限制

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 初始化
pipeline = VideoVaultPipeline(local_mode=Config.LOCAL_MODE)
if not Config.LOCAL_MODE:
    video_dao = VideoDAO()
    audit_dao = AuditLogDAO()

# 尝试初始化AI Agent
try:
    ai_agent = VideoVaultAgent()
    ai_agent_available = True
except:
    ai_agent_available = False
    print("⚠️  AI Agent未配置，相关功能将不可用")


def allowed_file(filename):
    """检查文件扩展名"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'ok',
        'mode': 'local' if Config.LOCAL_MODE else 'cloud',
        'ai_agent_available': ai_agent_available,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/videos/upload', methods=['POST'])
def upload_video():
    """上传视频并开始处理"""
    try:
        # 检查文件
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': f'不支持的文件类型，仅支持: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

        # 保存文件
        filename = secure_filename(file.filename)
        video_id = str(uuid.uuid4())
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{video_id}_{filename}")
        file.save(file_path)

        # 异步处理视频（这里简化为同步，实际可用celery等）
        # 在生产环境中应该用后台任务
        result = pipeline.process_video(
            file_path,
            output_dir=os.path.join(app.config['UPLOAD_FOLDER'], 'output')
        )

        return jsonify({
            'success': True,
            'video_id': result['video_id'],
            'sensitive_count': result.get('sensitive_count', 0),
            'output_path': result.get('output_path', ''),
            'message': '视频处理完成'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/videos', methods=['GET'])
def list_videos():
    """获取视频列表"""
    try:
        if Config.LOCAL_MODE:
            # 本地模式：扫描输出目录
            output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'output')
            videos = []

            if os.path.exists(output_dir):
                for filename in os.listdir(output_dir):
                    if filename.endswith('_sanitized.mp4'):
                        video_id = filename.replace('_sanitized.mp4', '')
                        videos.append({
                            'video_id': video_id,
                            'filename': filename,
                            'status': 'completed',
                            'created_at': datetime.now().isoformat()
                        })

            return jsonify({'videos': videos, 'total': len(videos)})
        else:
            # 云端模式：从数据库查询
            status = request.args.get('status')
            limit = int(request.args.get('limit', 50))
            videos = video_dao.list_videos(status=status, limit=limit)
            return jsonify({'videos': videos, 'total': len(videos)})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/videos/<video_id>', methods=['GET'])
def get_video_detail(video_id):
    """获取视频详情"""
    try:
        if Config.LOCAL_MODE:
            return jsonify({
                'video_id': video_id,
                'status': 'completed',
                'message': '本地模式，详细信息请查看数据库'
            })
        else:
            video = video_dao.get_video_by_id(video_id)
            if not video:
                return jsonify({'error': '视频不存在'}), 404

            # 获取审计日志
            audit_logs = audit_dao.get_audit_logs_by_video(video_id)
            audit_stats = audit_dao.count_sensitive_by_type(video_id)

            return jsonify({
                'video': video,
                'audit_logs': audit_logs,
                'audit_stats': audit_stats
            })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/videos/<video_id>/download', methods=['GET'])
def download_video(video_id):
    """下载处理后的视频"""
    try:
        output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'output')
        video_file = os.path.join(output_dir, f"{video_id}_sanitized.mp4")

        if not os.path.exists(video_file):
            return jsonify({'error': '视频文件不存在'}), 404

        return send_file(video_file, as_attachment=True, download_name=f"sanitized_{video_id}.mp4")

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/audit/logs', methods=['GET'])
def get_audit_logs():
    """获取审计日志"""
    try:
        if Config.LOCAL_MODE:
            # 本地模式：从文件系统读取审计日志
            output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'output')
            video_id = request.args.get('video_id')
            all_logs = []

            if not os.path.exists(output_dir):
                return jsonify({
                    'logs': [],
                    'total': 0
                })

            # 如果指定了video_id，只读取该视频的日志
            if video_id:
                video_dir = os.path.join(output_dir, video_id)
                audit_file = os.path.join(video_dir, 'audit_log.json')
                if os.path.exists(audit_file):
                    with open(audit_file, 'r', encoding='utf-8') as f:
                        audit_data = json.load(f)
                        all_logs = audit_data.get('detections', [])
            else:
                # 读取所有视频的审计日志
                video_files = [f for f in os.listdir(output_dir) if f.endswith('_sanitized.mp4')]
                for video_file in video_files:
                    vid = video_file.replace('_sanitized.mp4', '')
                    video_dir = os.path.join(output_dir, vid)
                    audit_file = os.path.join(video_dir, 'audit_log.json')
                    if os.path.exists(audit_file):
                        try:
                            with open(audit_file, 'r', encoding='utf-8') as f:
                                audit_data = json.load(f)
                                logs = audit_data.get('detections', [])
                                # 添加video_id和video_title字段
                                for log in logs:
                                    log['video_id'] = vid
                                    log['video_title'] = audit_data.get('video_title', vid)
                                all_logs.extend(logs)
                        except Exception as e:
                            print(f"读取审计日志失败: {audit_file}, 错误: {e}")

            # 按时间排序
            all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            return jsonify({
                'logs': all_logs,
                'total': len(all_logs)
            })

        video_id = request.args.get('video_id')
        days = int(request.args.get('days', 7))

        if video_id:
            logs = audit_dao.get_audit_logs_by_video(video_id)
        else:
            logs = audit_dao.get_recent_audit_logs(days=days)

        return jsonify({
            'logs': logs,
            'total': len(logs)
        })

    except Exception as e:
        print(f"获取审计日志失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/audit/stats', methods=['GET'])
def get_audit_stats():
    """获取审计统计"""
    try:
        if Config.LOCAL_MODE:
            # 本地模式：从文件系统读取统计数据
            output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'output')

            if not os.path.exists(output_dir):
                return jsonify({
                    'total_detections': 0,
                    'by_type': {},
                    'period_days': 7
                })

            # 统计所有审计日志
            all_detections = []
            video_files = [f for f in os.listdir(output_dir) if f.endswith('_sanitized.mp4')]

            for video_file in video_files:
                video_id = video_file.replace('_sanitized.mp4', '')
                video_dir = os.path.join(output_dir, video_id)
                audit_file = os.path.join(video_dir, 'audit_log.json')

                if os.path.exists(audit_file):
                    try:
                        with open(audit_file, 'r', encoding='utf-8') as f:
                            audit_data = json.load(f)
                            all_detections.extend(audit_data.get('detections', []))
                    except Exception as e:
                        print(f"读取审计日志失败: {audit_file}, 错误: {e}")

            # 统计各类敏感信息数量
            type_stats = {}
            for detection in all_detections:
                t = detection.get('type', 'unknown')
                type_stats[t] = type_stats.get(t, 0) + 1

            return jsonify({
                'total_detections': len(all_detections),
                'by_type': type_stats,
                'period_days': 0  # 本地模式不区分时间段
            })

        days = int(request.args.get('days', 7))
        logs = audit_dao.get_recent_audit_logs(days=days)

        # 统计各类敏感信息数量
        type_stats = {}
        for log in logs:
            t = log['sensitive_type']
            type_stats[t] = type_stats.get(t, 0) + 1

        return jsonify({
            'total_detections': len(logs),
            'by_type': type_stats,
            'period_days': days
        })

    except Exception as e:
        print(f"获取审计统计失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/chat', methods=['POST'])
def ai_chat():
    """AI Agent对话接口"""
    try:
        if not ai_agent_available:
            return jsonify({'error': 'AI Agent未配置'}), 503

        data = request.get_json()
        message = data.get('message', '')

        if not message:
            return jsonify({'error': '消息不能为空'}), 400

        # 调用AI Agent
        response = ai_agent.chat(message)

        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/reset', methods=['POST'])
def ai_reset():
    """重置AI Agent对话"""
    try:
        if not ai_agent_available:
            return jsonify({'error': 'AI Agent未配置'}), 503

        ai_agent.reset_conversation()
        return jsonify({'message': '对话已重置'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats/dashboard', methods=['GET'])
def get_dashboard_stats():
    """获取仪表盘统计数据"""
    try:
        if Config.LOCAL_MODE:
            # 本地模式：从文件系统读取数据
            output_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'output')

            if not os.path.exists(output_dir):
                return jsonify({
                    'total_videos': 0,
                    'processing_videos': 0,
                    'completed_videos': 0,
                    'total_sensitive_detections': 0,
                    'high_risk_videos': 0,
                    'recent_activity': []
                })

            # 统计视频文件（_sanitized.mp4结尾的文件）
            video_files = [f for f in os.listdir(output_dir) if f.endswith('_sanitized.mp4')]
            total_videos = len(video_files)

            # 读取每个视频的审计日志
            total_detections = 0
            high_risk_videos = 0
            recent_activity = []

            for video_file in video_files:
                video_id = video_file.replace('_sanitized.mp4', '')
                video_dir = os.path.join(output_dir, video_id)
                audit_file = os.path.join(video_dir, 'audit_log.json')

                if os.path.exists(audit_file):
                    try:
                        with open(audit_file, 'r', encoding='utf-8') as f:
                            audit_data = json.load(f)
                            detections = audit_data.get('total_detections', 0)
                            total_detections += detections

                            if detections >= 5:
                                high_risk_videos += 1

                            # 添加到最近活动
                            for detection in audit_data.get('detections', [])[:3]:
                                recent_activity.append({
                                    'video_id': video_id,
                                    'video_title': audit_data.get('video_title', video_id),
                                    'sensitive_type': detection.get('type', 'unknown'),
                                    'timestamp': detection.get('timestamp', ''),
                                    'confidence': detection.get('confidence', 0),
                                    'text': detection.get('text', '')[:50]
                                })
                    except Exception as e:
                        print(f"读取审计日志失败: {audit_file}, 错误: {e}")

            # 按时间排序最近活动
            recent_activity.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            return jsonify({
                'total_videos': total_videos,
                'processing_videos': 0,
                'completed_videos': total_videos,
                'total_sensitive_detections': total_detections,
                'high_risk_videos': high_risk_videos,
                'recent_activity': recent_activity[:10]
            })

        videos = video_dao.list_videos(limit=1000)
        logs = audit_dao.get_recent_audit_logs(days=30)

        stats = {
            'total_videos': len(videos),
            'processing_videos': len([v for v in videos if v['status'] == 'processing']),
            'completed_videos': len([v for v in videos if v['status'] == 'completed']),
            'total_sensitive_detections': len(logs),
            'high_risk_videos': len([v for v in videos if v['sensitive_count'] >= 5]),
            'recent_activity': logs[:10]
        }

        return jsonify(stats)

    except Exception as e:
        print(f"获取仪表盘统计失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/data/clear', methods=['POST'])
def clear_data():
    """清空所有处理数据"""
    try:
        import shutil

        if Config.LOCAL_MODE:
            # 本地模式：删除uploads目录下的所有文件
            upload_dir = app.config['UPLOAD_FOLDER']
            output_dir = os.path.join(upload_dir, 'output')

            deleted_count = 0
            errors = []

            # 删除output目录
            if os.path.exists(output_dir):
                try:
                    shutil.rmtree(output_dir)
                    os.makedirs(output_dir, exist_ok=True)
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"删除output目录失败: {e}")

            # 删除上传的原始视频文件
            if os.path.exists(upload_dir):
                for item in os.listdir(upload_dir):
                    item_path = os.path.join(upload_dir, item)
                    # 跳过output目录
                    if item == 'output':
                        continue
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                            deleted_count += 1
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                            deleted_count += 1
                    except Exception as e:
                        errors.append(f"删除 {item} 失败: {e}")

            message = f"已清空 {deleted_count} 个文件/目录"
            if errors:
                message += f"，{len(errors)} 个错误"

            return jsonify({
                'success': True,
                'message': message,
                'deleted_count': deleted_count,
                'errors': errors
            })

        else:
            # 云端模式：清空数据库（谨慎操作！）
            return jsonify({
                'error': '云端模式下不支持此操作，请手动清理数据库'
            }), 403

    except Exception as e:
        print(f"清空数据失败: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Video Vault Backend API Server")
    print("=" * 60)
    print(f"运行模式: {'本地测试' if Config.LOCAL_MODE else '云端生产'}")
    print(f"AI Agent: {'可用' if ai_agent_available else '不可用'}")
    print(f"上传目录: {UPLOAD_FOLDER}")
    print("=" * 60)
    print("\nAPI接口:")
    print("  GET  /api/health           - 健康检查")
    print("  POST /api/videos/upload    - 上传视频")
    print("  GET  /api/videos           - 视频列表")
    print("  GET  /api/videos/<id>      - 视频详情")
    print("  GET  /api/audit/logs       - 审计日志")
    print("  POST /api/ai/chat          - AI对话")
    print("=" * 60)
    print("\n启动服务器在 http://127.0.0.1:5000\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
