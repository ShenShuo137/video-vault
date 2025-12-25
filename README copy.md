# Video Vault - 企业会议视频智能安全平台

基于华为云Serverless架构的会议视频DLP(数据泄漏防护)系统

## 项目概述

Video Vault 通过"双重安全防线"保护企业会议视频：
- **第一道防线**: DLP视觉防火墙 - 自动检测并脱敏视频中的敏感信息
- **第二道防线**: 数字水印溯源 - 为每个下载者植入唯一水印(未来功能)

## 功能特性

### MVP版本 (当前实现)
- ✅ 视频自动切片处理
- ✅ OCR文字识别
- ✅ 敏感信息检测(API Key、密码、身份证、手机号等)
- ✅ 自动脱敏处理(高斯模糊/马赛克)
- ✅ 审计日志记录
- ✅ AI Agent智能查询
- ✅ 本地测试模式

### 进阶功能 (计划中)
- ⏳ 频域数字水印
- ⏳ Web前端界面
- ⏳ Zoom会议自动集成

## 项目结构

```
video-vault/
├── functions/              # Serverless云函数
│   ├── video_slicer/      # 视频切片函数
│   ├── dlp_scanner/       # DLP扫描函数
│   ├── video_merger/      # 视频合并函数
│   └── ai_agent/          # AI Agent函数
├── shared/                # 共享代码库
│   ├── config.py          # 配置管理
│   ├── db_connector.py    # 数据库操作
│   ├── obs_helper.py      # OBS对象存储
│   ├── video_slicer.py    # 视频切片模块
│   ├── dlp_scanner.py     # DLP扫描模块
│   └── video_merger.py    # 视频合并模块
├── sql/                   # 数据库脚本
│   └── schema.sql         # 表结构定义
├── local_tests/           # 本地测试
│   ├── local_test_pipeline.py  # 完整流程测试
│   └── create_test_video.py    # 测试视频生成
├── requirements.txt       # Python依赖
└── .env.example          # 环境变量模板
```

## 快速开始

### 1. 环境准备

```bash
# 激活conda环境
conda activate sag

# 安装依赖
pip install -r requirements.txt

# 安装Tesseract OCR (Windows)
# 下载: https://github.com/UB-Mannheim/tesseract/wiki
# 添加到PATH环境变量

# 安装FFmpeg (可选，用于视频合并)
# 下载: https://ffmpeg.org/download.html
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
copy .env.example .env

# 编辑.env文件，填写配置
notepad .env
```

### 3. 本地测试

```bash
# 创建测试视频(包含模拟敏感信息)
python local_tests/create_test_video.py

# 运行完整DLP流程测试
python local_tests/local_test_pipeline.py

# 或者指定自己的视频
python local_tests/local_test_pipeline.py path/to/your/video.mp4
```

## 敏感信息检测规则

系统会自动检测以下类型的敏感信息：

| 类型 | 正则表达式 | 示例 |
|------|-----------|------|
| OpenAI Key | `sk-[A-Za-z0-9]{48}` | sk-abcd1234... |
| AWS Key | `AKIA[0-9A-Z]{16}` | AKIAIOSFODNN7EXAMPLE |
| 华为云AK | `[A-Z0-9]{20}` | ABCDEFGHIJ1234567890 |
| 密码 | `password[:\s=]+\S+` | password=123456 |
| 身份证 | `\d{17}[\dXx]` | 110101199001011234 |
| 手机号 | `1[3-9]\d{9}` | 13800138000 |

## 数据库设计

### 核心表结构

1. **videos** - 视频元数据表
   - 存储视频基本信息、处理状态

2. **audit_logs** - 审计日志表
   - 记录每次敏感信息检测详情

3. **watermark_mapping** - 水印溯源表(预留)
   - 存储水印与用户的映射关系

详见: `sql/schema.sql`

## AI Agent功能

AI Agent充当"首席安全官(CISO)"角色，支持智能查询：

### 工具集

- `query_audit_logs` - 查询审计日志
- `get_video_status` - 查询视频处理状态
- `list_sensitive_videos` - 列出高风险视频
- `extract_watermark` - 提取水印信息(预留)

### 示例对话

```
用户: 上周的架构评审会，有没有泄露敏感数据？
AI: 查询审计日志发现，该会议视频检测到3次数据库密码暴露和1次AccessKey，
   已自动进行高斯模糊处理，未造成实质泄露。
```

## 华为云部署

### 1. 创建OBS Bucket

```bash
# 在华为云控制台创建OBS存储桶
Bucket名称: video-vault-storage
区域: 华北-北京四(cn-north-4)
```

### 2. 创建RDS数据库

```bash
# 创建MySQL数据库实例
# 执行 sql/schema.sql 初始化表结构
```

### 3. 部署云函数

```bash
# 打包函数代码
cd functions/video_slicer
zip -r video_slicer.zip .

# 上传到FunctionGraph
# 在华为云控制台手动上传或使用CLI
```

### 4. 配置触发器

- 为video_slicer函数配置OBS触发器
- 监听视频上传事件自动触发处理

## 开发路线图

- [x] 核心DLP功能
- [x] 本地测试流程
- [ ] AI Agent集成
- [ ] 云函数封装
- [ ] 华为云部署
- [ ] 频域水印
- [ ] Web前端

## 技术栈

- **语言**: Python 3.11
- **视频处理**: OpenCV, FFmpeg
- **OCR**: Pytesseract
- **数据库**: MySQL (华为云RDS)
- **云服务**: 华为云 FunctionGraph, OBS, OCR
- **AI**: OpenAI API / 通义千问 / 华为云Pangu

## 许可证

MIT License

## 联系方式

如有问题，请提交Issue或联系开发团队。
