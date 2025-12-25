"""
生成包含敏感信息的测试视频
用于测试DLP功能
"""
import cv2
import numpy as np
import os


def create_test_video_with_sensitive_info(output_path='./test_video.mp4', duration=10, fps=30):
    """
    创建包含模拟敏感信息的测试视频
    :param output_path: 输出路径
    :param duration: 视频时长(秒)
    :param fps: 帧率
    """
    width, height = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # 定义测试场景(每个场景显示不同的敏感信息)
    scenes = [
        {
            'duration': 3,
            'text': [
                'AWS Configuration',
                'AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE',
                'AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG',
            ],
            'color': (255, 255, 255)
        },
        {
            'duration': 3,
            'text': [
                'OpenAI API Key',
                'sk-abcd1234efgh5678ijkl9012mnop3456qrst7890uvwx',
                'Never share your API keys!',
            ],
            'color': (100, 255, 100)
        },
        {
            'duration': 2,
            'text': [
                'Database Credentials',
                'DB_HOST=192.168.1.100',
                'DB_USER=admin',
                'DB_PASSWORD=SuperSecret123!',
            ],
            'color': (255, 200, 100)
        },
        {
            'duration': 2,
            'text': [
                'Personal Information',
                'ID Card: 110101199001011234',
                'Phone: 13800138000',
            ],
            'color': (255, 100, 100)
        }
    ]

    current_time = 0
    scene_idx = 0

    for frame_num in range(duration * fps):
        # 创建黑色背景
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # 确定当前场景
        while scene_idx < len(scenes) and current_time >= sum(s['duration'] for s in scenes[:scene_idx + 1]):
            scene_idx += 1

        if scene_idx < len(scenes):
            scene = scenes[scene_idx]

            # 添加标题
            cv2.putText(frame, f'Test Scene {scene_idx + 1}', (50, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)

            # 添加场景文字
            y_offset = 250
            for line in scene['text']:
                cv2.putText(frame, line, (100, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, scene['color'], 2)
                y_offset += 80

            # 添加警告标识
            cv2.putText(frame, '⚠️ SENSITIVE INFORMATION ⚠️', (300, height - 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

        # 添加时间戳
        cv2.putText(frame, f'Time: {current_time:.1f}s', (width - 300, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)

        out.write(frame)
        current_time = frame_num / fps

    out.release()
    print(f"✅ 测试视频已生成: {output_path}")
    print(f"   时长: {duration}秒")
    print(f"   分辨率: {width}x{height}")
    print(f"   包含 {len(scenes)} 个测试场景")
    print(f"   文件大小: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")


def main():
    """主函数"""
    print("=" * 60)
    print("Video Vault - 测试视频生成工具")
    print("=" * 60 + "\n")

    output_dir = os.path.dirname(__file__)
    output_path = os.path.join(output_dir, 'test_video.mp4')

    print("生成包含敏感信息的测试视频...\n")
    create_test_video_with_sensitive_info(output_path, duration=10, fps=30)

    print("\n" + "=" * 60)
    print("生成完成! 可以使用以下命令测试:")
    print(f"python local_test_pipeline.py {output_path}")
    print("=" * 60)


if __name__ == '__main__':
    main()
