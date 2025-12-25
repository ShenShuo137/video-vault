-- Video Vault 数据库表结构设计
-- 数据库名称: video_vault

CREATE DATABASE IF NOT EXISTS video_vault DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE video_vault;

-- 1. 视频元数据表
CREATE TABLE IF NOT EXISTS videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_id VARCHAR(64) UNIQUE NOT NULL COMMENT '视频唯一ID (UUID)',
    title VARCHAR(255) NOT NULL COMMENT '视频标题',
    original_filename VARCHAR(255) COMMENT '原始文件名',
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    duration INT COMMENT '视频时长(秒)',
    file_size BIGINT COMMENT '文件大小(字节)',
    status ENUM('uploading', 'processing', 'completed', 'failed') DEFAULT 'uploading' COMMENT '处理状态',
    obs_input_path VARCHAR(512) COMMENT 'OBS输入路径',
    obs_output_path VARCHAR(512) COMMENT 'OBS输出路径',
    output_url VARCHAR(512) COMMENT '处理后的视频下载URL',
    sensitive_count INT DEFAULT 0 COMMENT '检测到的敏感信息数量',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_video_id (video_id),
    INDEX idx_status (status),
    INDEX idx_upload_time (upload_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='视频元数据表';

-- 2. 审计日志表
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_id VARCHAR(64) NOT NULL COMMENT '关联的视频ID',
    slice_index INT COMMENT '视频切片索引',
    frame_id INT COMMENT '帧编号',
    timestamp_in_video DECIMAL(10,2) COMMENT '视频中的时间戳(秒)',
    sensitive_type VARCHAR(50) NOT NULL COMMENT '敏感信息类型: openai_key/aws_key/password/id_card/phone等',
    detected_text TEXT COMMENT '检测到的文字内容(脱敏后)',
    confidence DECIMAL(5,2) COMMENT 'OCR识别置信度',
    bbox_x INT COMMENT '边界框X坐标',
    bbox_y INT COMMENT '边界框Y坐标',
    bbox_width INT COMMENT '边界框宽度',
    bbox_height INT COMMENT '边界框高度',
    action_taken VARCHAR(50) DEFAULT 'blurred' COMMENT '采取的行动: blurred/masked',
    detected_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '检测时间',
    INDEX idx_video_id (video_id),
    INDEX idx_sensitive_type (sensitive_type),
    INDEX idx_detected_time (detected_time),
    FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='敏感信息审计日志表';

-- 3. 水印溯源表 (为未来功能预留)
CREATE TABLE IF NOT EXISTS watermark_mapping (
    id INT AUTO_INCREMENT PRIMARY KEY,
    watermark_id VARCHAR(64) UNIQUE NOT NULL COMMENT '水印唯一ID',
    video_id VARCHAR(64) NOT NULL COMMENT '关联的视频ID',
    user_id VARCHAR(64) NOT NULL COMMENT '下载用户ID',
    user_name VARCHAR(100) COMMENT '用户姓名',
    user_email VARCHAR(100) COMMENT '用户邮箱',
    department VARCHAR(100) COMMENT '部门',
    download_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '下载时间',
    download_ip VARCHAR(45) COMMENT '下载IP地址',
    watermark_data TEXT COMMENT '水印嵌入的数据(JSON格式)',
    status ENUM('active', 'extracted', 'leaked') DEFAULT 'active' COMMENT '状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_watermark_id (watermark_id),
    INDEX idx_video_id (video_id),
    INDEX idx_user_id (user_id),
    INDEX idx_download_time (download_time),
    FOREIGN KEY (video_id) REFERENCES videos(video_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='水印溯源映射表';

-- 4. 系统配置表 (可选)
CREATE TABLE IF NOT EXISTS system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    description VARCHAR(255) COMMENT '配置描述',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- 插入默认配置
INSERT INTO system_config (config_key, config_value, description) VALUES
('dlp_enabled', 'true', 'DLP功能是否启用'),
('watermark_enabled', 'false', '水印功能是否启用'),
('ocr_confidence_threshold', '0.6', 'OCR识别置信度阈值'),
('blur_intensity', '51', '高斯模糊强度(奇数)'),
('slice_duration', '60', '视频切片时长(秒)')
ON DUPLICATE KEY UPDATE config_value=VALUES(config_value);
