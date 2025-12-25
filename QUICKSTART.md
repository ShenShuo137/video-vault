# Video Vault - 快速开始指南

## 🚀 最快上手方式

### 方式1: 测试DLP功能（无需数据库和Web界面）

```bash
# 1. 安装Python依赖
pip install -r requirements.txt

# 2. 配置环境变量
copy .env.example .env
# 编辑.env，设置 LOCAL_MODE=true

# 3. 生成测试视频
python local_tests/create_test_video.py

# 4. 运行DLP处理
python local_tests/local_test_pipeline.py
```

**注意事项:**
- 需要安装Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
- 可选安装FFmpeg: https://ffmpeg.org/download.html

### 方式2: 运行Web界面（推荐）

#### 第1步: 后端准备

```bash
# 1. 安装Python依赖
pip install -r requirements.txt
pip install Flask Flask-CORS

# 2. 配置.env
copy .env.example .env
# 设置 LOCAL_MODE=true (本地测试)

# 3. 启动Flask后端
python backend/app.py
```

后端运行在: `http://127.0.0.1:5000`

#### 第2步: 前端准备

**选项A - 使用自动脚本 (Windows):**
```bash
# 直接运行批处理脚本
setup-frontend.bat
```

**选项B - 手动创建:**
```bash
# 1. 创建Vue 3项目
npm create vite@latest frontend -- --template vue

# 2. 进入目录并安装依赖
cd frontend
npm install

# 3. 安装UI库
npm install axios element-plus @element-plus/icons-vue vue-router@4 pinia

# 4. 按照 WEB_DEPLOYMENT.md 配置文件
# 主要需要创建:
#   - src/api/config.js
#   - src/api/video.js
#   - src/router/index.js
#   - 修改 src/main.js
#   - 修改 src/App.vue

# 5. 启动开发服务器
npm run dev
```

前端运行在: `http://localhost:5173`

#### 第3步: 测试

1. 打开浏览器访问 `http://localhost:5173`
2. 点击"上传视频"
3. 上传测试视频（或用 `local_tests/create_test_video.py` 生成的视频）
4. 查看处理进度和结果

## 📋 详细文档

- **README.md** - 项目整体介绍
- **NEXT_STEPS.md** - 详细开发和部署指南
- **WEB_DEPLOYMENT.md** - Web界面完整配置指南

## 🔧 依赖安装

### Python依赖

```bash
pip install opencv-python pytesseract pymysql Flask Flask-CORS
pip install huaweicloudsdkcore huaweicloudsdkobs huaweicloudsdkocr
pip install python-dotenv requests openai
```

### 系统依赖

**Tesseract OCR (必需):**
- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Linux: `sudo apt-get install tesseract-ocr`
- Mac: `brew install tesseract`

**FFmpeg (推荐):**
- Windows: https://ffmpeg.org/download.html
- Linux: `sudo apt-get install ffmpeg`
- Mac: `brew install ffmpeg`

### Node.js依赖

```bash
# 前端依赖
cd frontend
npm install axios element-plus @element-plus/icons-vue vue-router pinia
```

## ⚙️ 配置说明

### 本地测试模式 (.env)

```env
LOCAL_MODE=true
LOCAL_STORAGE_PATH=./local_tests/storage
```

这种模式下:
- ✅ 不需要数据库
- ✅ 不需要华为云配置
- ✅ 文件存储在本地
- ⚠️  审计日志只打印不存储

### 完整功能模式 (.env)

```env
LOCAL_MODE=false

# 华为云配置
HUAWEI_CLOUD_AK=your_ak
HUAWEI_CLOUD_SK=your_sk
OBS_BUCKET_NAME=video-vault-storage

# 数据库配置
DB_HOST=your_rds_host
DB_PORT=3306
DB_NAME=video_vault
DB_USER=root
DB_PASSWORD=your_password

# AI Agent配置
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-4
```

## 🎯 功能测试清单

### DLP功能测试
- [ ] 视频切片
- [ ] OCR识别
- [ ] 敏感信息检测
- [ ] 脱敏处理（模糊/马赛克）
- [ ] 视频合并

### Web界面测试
- [ ] 上传视频
- [ ] 查看视频列表
- [ ] 下载处理后的视频
- [ ] 查看审计日志
- [ ] AI助手对话

### AI Agent测试
- [ ] 查询审计日志
- [ ] 列出高风险视频
- [ ] 生成安全报告

## 🐛 常见问题

**Q: Tesseract not found**
```bash
# 确保Tesseract已安装并添加到PATH
where tesseract  # Windows
which tesseract  # Linux/Mac
```

**Q: 前端无法连接后端**
```bash
# 确保后端已启动
# 检查 frontend/src/api/config.js 中的 baseURL
```

**Q: 视频处理很慢**
```bash
# 正常现象，OCR识别需要时间
# 建议先用短视频测试（<30秒）
```

**Q: AI Agent不可用**
```bash
# 需要配置LLM_API_KEY
# 支持OpenAI、通义千问等兼容API
```

## 📞 需要帮助？

- 查看代码注释
- 阅读详细文档
- 检查日志输出
