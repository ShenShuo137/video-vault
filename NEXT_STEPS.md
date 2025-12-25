# Video Vault - 下一步操作指南

## 当前进度

✅ **已完成的工作:**
1. 项目基础架构设计
2. 数据库表结构设计 (`sql/schema.sql`)
3. 共享工具类实现 (配置、数据库、OBS)
4. 核心DLP功能模块:
   - 视频切片 (`shared/video_slicer.py`)
   - OCR识别与敏感信息检测 (`shared/dlp_scanner.py`)
   - 脱敏处理 (高斯模糊/马赛克)
   - 视频合并 (`shared/video_merger.py`)
5. 完整本地测试流程 (`local_tests/local_test_pipeline.py`)
6. AI Agent智能助手 (`functions/ai_agent/`)
7. 测试工具 (`local_tests/create_test_video.py`)

## 下一步: 本地测试验证

### 步骤1: 安装依赖环境

```bash
# 1. 激活conda环境
conda activate sag

# 2. 安装Python依赖
pip install -r requirements.txt

# 3. 安装Tesseract OCR (Windows)
# 下载安装包: https://github.com/UB-Mannheim/tesseract/wiki
# 安装后添加到系统PATH: C:\Program Files\Tesseract-OCR

# 4. 安装FFmpeg (可选，用于视频合并)
# 下载: https://ffmpeg.org/download.html
# 解压后添加bin目录到系统PATH
```

### 步骤2: 配置环境变量

```bash
# 复制环境变量模板
copy .env.example .env

# 编辑.env文件
notepad .env
```

**最小配置 (本地测试模式):**
```env
# 本地测试配置
LOCAL_MODE=true
LOCAL_STORAGE_PATH=./local_tests/storage

# AI Agent配置 (如果要测试AI功能)
LLM_API_KEY=your_api_key_here
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4
```

### 步骤3: 生成测试视频

```bash
# 生成包含模拟敏感信息的测试视频
python local_tests/create_test_video.py
```

这将在 `local_tests/` 目录下生成 `test_video.mp4`，包含:
- AWS Key
- OpenAI API Key
- 数据库密码
- 身份证号和手机号

### 步骤4: 运行DLP处理流程

```bash
# 运行完整的DLP处理流程
python local_tests/local_test_pipeline.py

# 或者指定自己的视频
python local_tests/local_test_pipeline.py path/to/your/video.mp4
```

**预期结果:**
- ✅ 视频被切分成多个片段
- ✅ OCR识别视频中的文字
- ✅ 检测并定位敏感信息
- ✅ 对敏感区域进行高斯模糊处理
- ✅ 合并生成最终脱敏视频
- ✅ 输出审计日志

处理后的视频位于: `local_tests/output/<video_id>_sanitized.mp4`

### 步骤5: 测试AI Agent (可选)

```bash
# 运行AI Agent交互式测试
python functions/ai_agent/agent.py
```

**示例对话:**
```
您: 最近检测到了哪些敏感信息?
AI: [调用工具查询并分析]

您: 生成安全报告
AI: [生成详细的安全审计报告]
```

## 下一步: 华为云部署

### 准备工作

1. **开通华为云服务:**
   - 对象存储 OBS
   - 云数据库 RDS MySQL
   - 函数工作流 FunctionGraph
   - OCR服务 (可选)

2. **获取凭证:**
   - Access Key (AK)
   - Secret Access Key (SK)
   - 项目ID

### 部署流程

#### 1. 创建OBS Bucket

```bash
# 在华为云控制台创建OBS存储桶
名称: video-vault-storage
区域: cn-north-4 (华北-北京四)
权限: 私有

# 创建目录结构:
/videos/           # 原始视频
/slices/           # 视频切片
/processed/        # 处理后的视频
/output/           # 最终输出
```

#### 2. 创建RDS数据库

```bash
# 在华为云控制台创建MySQL实例
版本: MySQL 8.0
规格: 按需选择
网络: VPC (与FunctionGraph同区域)

# 连接数据库并执行初始化脚本
mysql -h <rds_host> -u root -p
source sql/schema.sql
```

#### 3. 封装云函数

为每个模块创建FunctionGraph入口函数:

**示例: `functions/video_slicer/index.py`**
```python
import sys
sys.path.insert(0, '/opt/python')  # 添加依赖层路径

from shared.video_slicer import VideoSlicer
from shared.obs_helper import OBSHelper

def handler(event, context):
    """FunctionGraph入口函数"""
    # 从OBS触发事件获取视频信息
    obs_key = event['obs']['object']['key']

    # 下载视频
    obs = OBSHelper()
    local_path = f'/tmp/{obs_key}'
    obs.download_file(obs_key, local_path)

    # 切片处理
    slicer = VideoSlicer()
    slices = slicer.slice_video(local_path, '/tmp/slices')

    # 上传切片到OBS
    for slice_file in slices:
        obs.upload_file(slice_file, f'slices/{os.path.basename(slice_file)}')

    return {'status': 'success', 'slices_count': len(slices)}
```

#### 4. 创建依赖层

```bash
# 创建依赖层目录
mkdir layer
cd layer
pip install -r ../requirements.txt -t python/

# 打包依赖层
zip -r layer.zip python/

# 在FunctionGraph控制台上传依赖层
```

#### 5. 配置触发器

```
video_slicer函数:
  - 触发器类型: OBS
  - 事件: ObjectCreated
  - Bucket: video-vault-storage
  - 前缀: videos/

dlp_scanner函数:
  - 触发器类型: OBS
  - 事件: ObjectCreated
  - Bucket: video-vault-storage
  - 前缀: slices/
```

#### 6. 更新环境变量

在.env中添加华为云配置:
```env
LOCAL_MODE=false

HUAWEI_CLOUD_AK=your_ak_here
HUAWEI_CLOUD_SK=your_sk_here
HUAWEI_CLOUD_REGION=cn-north-4

OBS_BUCKET_NAME=video-vault-storage
OBS_ENDPOINT=obs.cn-north-4.myhuaweicloud.com

DB_HOST=your_rds_host
DB_PORT=3306
DB_NAME=video_vault
DB_USER=root
DB_PASSWORD=your_password
```

## 问题排查

### 常见问题

**1. Tesseract OCR找不到**
```bash
# 确保Tesseract已添加到PATH
where tesseract

# 如果没有，手动添加到PATH:
# 系统属性 -> 环境变量 -> Path -> 新建 -> C:\Program Files\Tesseract-OCR
```

**2. FFmpeg找不到**
```bash
# 如果没有FFmpeg，系统会自动降级使用OpenCV合并
# 或者安装FFmpeg并添加到PATH
```

**3. OpenCV导入错误**
```bash
pip uninstall opencv-python opencv-contrib-python
pip install opencv-python==4.8.1.78
```

**4. 数据库连接失败**
```bash
# 本地测试模式不需要数据库
# 确保.env中 LOCAL_MODE=true
```

## 后续优化方向

### 功能增强
1. **频域水印**: 实现DCT/DFT水印嵌入与提取
2. **Web界面**: 使用Flask开发管理后台
3. **实时监控**: 添加处理进度监控面板
4. **批量处理**: 支持同时处理多个视频

### 性能优化
1. **并行处理**: 利用FunctionGraph并发能力
2. **缓存优化**: 对重复视频跳过处理
3. **增量处理**: 只处理变化的帧

### 安全增强
1. **权限管理**: 添加RBAC权限控制
2. **加密存储**: OBS对象加密
3. **审计增强**: 详细的操作日志

## 联系与支持

如遇到问题，请检查:
1. `README.md` - 项目整体说明
2. 各模块代码中的注释
3. `.env.example` - 环境变量配置示例

祝开发顺利! 🚀
