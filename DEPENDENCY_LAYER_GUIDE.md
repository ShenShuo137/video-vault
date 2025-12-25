# 华为云FunctionGraph依赖层打包指南

## 📦 依赖层说明

华为云FunctionGraph支持依赖层（Dependency Layer），可以将大型依赖和二进制文件打包上传，供函数使用。

**依赖层限制：**
- 单个依赖层最大 100MB（压缩后）
- 每个函数最多关联 5 个依赖层
- 解压后总大小不超过 500MB

---

## 🎯 方案选择

### 方案A：使用华为云服务（推荐）⭐

**优势：**
- ✅ 无需打包二进制文件
- ✅ 部署简单快速
- ✅ 冷启动快（<3秒）
- ✅ 稳定可靠

**依赖层内容：**
- Python依赖包（~30MB）
- 项目代码（~5MB）

**总计：** ~35MB

---

### 方案B：使用FFmpeg + Tesseract

**优势：**
- ✅ 完全自主控制
- ✅ 不依赖外部服务

**劣势：**
- ⚠️ FFmpeg约80-100MB
- ⚠️ Tesseract + 语言包约50-80MB
- ⚠️ 需要2-3个依赖层
- ⚠️ 冷启动慢（10-20秒）

**依赖层划分：**
1. **python-deps层**：Python依赖包（~30MB）
2. **ffmpeg层**：FFmpeg二进制（~90MB）
3. **tesseract层**：Tesseract + 中英文语言包（~70MB）

**总计：** ~190MB

---

## 📋 方案A：Python依赖层打包（推荐）

### 1. 创建打包目录

```bash
mkdir -p layers/python-deps/python
cd layers/python-deps
```

### 2. 安装Python依赖

```bash
# 使用华为云FunctionGraph的Python运行时
pip install -t python/ \
    opencv-python-headless==4.8.1.78 \
    numpy==1.24.3 \
    Pillow==10.0.0 \
    requests==2.31.0 \
    PyMySQL==1.1.0 \
    huaweicloudsdkcore==3.1.60 \
    huaweicloudsdkobs==3.23.3 \
    huaweicloudsdkocr==3.1.60 \
    huaweicloudsdkmpc==3.1.60 \
    huaweicloudsdkfunctiongraph==3.1.60
```

### 3. 添加项目代码

```bash
# 复制shared目录到python/
cp -r ../../shared python/
```

### 4. 打包

```bash
zip -r python-deps.zip python/
```

### 5. 上传到华为云

```bash
# 登录华为云控制台
# FunctionGraph > 依赖管理 > 创建依赖
# 上传 python-deps.zip
```

---

## 📋 方案B：完整依赖层打包

### 依赖层1: Python依赖

同方案A

---

### 依赖层2: FFmpeg二进制

#### 方法1: 使用预编译版本（推荐）

```bash
mkdir -p layers/ffmpeg/bin
cd layers/ffmpeg

# 下载静态编译版本
wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xf ffmpeg-release-amd64-static.tar.xz

# 提取二进制文件
cp ffmpeg-*-amd64-static/ffmpeg bin/
cp ffmpeg-*-amd64-static/ffprobe bin/

# 打包
cd ..
zip -r ffmpeg.zip ffmpeg/
```

#### 方法2: 自行编译（适合优化体积）

```bash
# 在Linux环境（或Docker）中编译
docker run -it --rm -v $(pwd):/workspace ubuntu:20.04 bash

apt-get update
apt-get install -y build-essential yasm pkg-config

# 下载FFmpeg源码
wget https://ffmpeg.org/releases/ffmpeg-6.0.tar.xz
tar -xf ffmpeg-6.0.tar.xz
cd ffmpeg-6.0

# 配置（最小化编译）
./configure \
  --prefix=/opt/ffmpeg \
  --enable-static \
  --disable-shared \
  --disable-doc \
  --disable-debug \
  --disable-network \
  --disable-filters \
  --enable-filter=scale,format,fps \
  --disable-encoders \
  --enable-encoder=libx264,aac \
  --disable-decoders \
  --enable-decoder=h264,aac \
  --disable-muxers \
  --enable-muxer=mp4 \
  --disable-demuxers \
  --enable-demuxer=mov

make -j$(nproc)
make install

# 打包
cd /workspace
mkdir -p layers/ffmpeg/bin
cp /opt/ffmpeg/bin/ffmpeg layers/ffmpeg/bin/
cp /opt/ffmpeg/bin/ffprobe layers/ffmpeg/bin/
cd layers
zip -r ffmpeg.zip ffmpeg/
```

**体积优化后：** 约60-80MB

---

### 依赖层3: Tesseract OCR

#### 下载预编译版本

```bash
mkdir -p layers/tesseract
cd layers/tesseract

# 下载Tesseract和语言包
# 方式1: 使用Ubuntu包
docker run -it --rm -v $(pwd):/workspace ubuntu:20.04 bash

apt-get update
apt-get install -y tesseract-ocr tesseract-ocr-eng tesseract-ocr-chi-sim

# 复制到工作目录
mkdir -p /workspace/usr
cp -r /usr/bin/tesseract /workspace/usr/bin/
cp -r /usr/share/tesseract-ocr /workspace/usr/share/

exit

# 打包
zip -r tesseract.zip usr/
```

**或者使用预编译版本：**

```bash
# 下载编译好的Tesseract
wget https://github.com/tesseract-ocr/tesseract/releases/download/5.3.0/tesseract-5.3.0.tar.gz

# 解压并打包
tar -xzf tesseract-5.3.0.tar.gz
cd tesseract-5.3.0
./configure --prefix=/opt/tesseract
make
make install

# 打包
cd /opt
zip -r tesseract.zip tesseract/
```

**体积优化：**
- 仅保留需要的语言包（eng + chi_sim）
- 删除不必要的文件（docs, examples）

**优化后：** 约50-70MB

---

## 📂 依赖层目录结构

### 方案A结构：

```
python-deps.zip
└── python/
    ├── cv2/                    # OpenCV
    ├── numpy/                  # NumPy
    ├── PIL/                    # Pillow
    ├── huaweicloudsdkcore/     # 华为云SDK
    ├── huaweicloudsdkobs/
    ├── huaweicloudsdkocr/
    ├── huaweicloudsdkmpc/
    ├── requests/
    └── shared/                 # 项目代码
        ├── config.py
        ├── video_slicer.py
        ├── dlp_scanner.py
        ├── video_merger.py
        ├── obs_helper.py
        ├── db_connector.py
        ├── ocr_service.py
        └── video_processing_service.py
```

### 方案B结构：

**1. python-deps.zip** (同上)

**2. ffmpeg.zip**
```
ffmpeg/
└── bin/
    ├── ffmpeg      # 85MB
    └── ffprobe     # 5MB
```

**3. tesseract.zip**
```
tesseract/
├── bin/
│   └── tesseract           # 10MB
└── share/
    └── tessdata/
        ├── eng.traineddata # 25MB
        └── chi_sim.traineddata # 35MB
```

---

## 🚀 上传依赖层到华为云

### 方法1: 控制台上传

1. 登录华为云控制台
2. 进入 **FunctionGraph** 服务
3. 左侧菜单选择 **依赖管理**
4. 点击 **创建依赖**
5. 填写信息：
   - **依赖包名称**: `python-deps` / `ffmpeg` / `tesseract`
   - **运行时**: Python 3.9
   - **上传方式**: 本地上传
   - **选择文件**: 上传 .zip 文件
6. 点击 **确定**

### 方法2: 命令行上传（推荐）

```bash
# 安装华为云CLI
pip install huaweicloudsdkcli

# 配置认证
hcloud configure

# 上传依赖层
hcloud FunctionGraph CreateDependency \
  --name "python-deps" \
  --runtime "Python3.9" \
  --file "python-deps.zip"

# 如果使用方案B，继续上传
hcloud FunctionGraph CreateDependency \
  --name "ffmpeg" \
  --runtime "Python3.9" \
  --file "ffmpeg.zip"

hcloud FunctionGraph CreateDependency \
  --name "tesseract" \
  --runtime "Python3.9" \
  --file "tesseract.zip"
```

---

## 🔧 函数中使用依赖层

### 方案A使用方式

**1. 关联依赖层**

在函数配置中关联 `python-deps` 依赖层

**2. 代码中引用**

```python
import sys
sys.path.insert(0, '/opt/python')  # 依赖层路径

# 直接导入
from shared.video_slicer import VideoSlicer
from shared.dlp_scanner import DLPScanner
import cv2
```

---

### 方案B使用方式

**1. 关联依赖层**

在函数配置中关联 3 个依赖层：
- `python-deps`
- `ffmpeg`
- `tesseract`

**2. 设置环境变量**

在函数配置中添加环境变量：

```bash
# FFmpeg路径
PATH=/opt/ffmpeg/bin:$PATH
LD_LIBRARY_PATH=/opt/ffmpeg/lib:$LD_LIBRARY_PATH

# Tesseract路径
TESSDATA_PREFIX=/opt/tesseract/share/tessdata
```

**3. 代码中使用**

```python
import sys
import os

sys.path.insert(0, '/opt/python')

# FFmpeg会自动从PATH中找到
from shared.video_merger import VideoMerger
merger = VideoMerger()
merger.merge(files, output)  # 自动使用/opt/ffmpeg/bin/ffmpeg

# Tesseract需要指定路径
from shared.ocr_service import OCRService
import pytesseract
pytesseract.pytesseract.tesseract_cmd = '/opt/tesseract/bin/tesseract'
ocr = OCRService()
```

---

## 📊 方案对比总结

| 特性 | 方案A (华为云服务) | 方案B (依赖层) |
|-----|-------------------|---------------|
| 部署难度 | ⭐ 简单 | ⭐⭐⭐ 复杂 |
| 包体积 | 35MB | 190MB |
| 冷启动时间 | 2-3秒 | 10-20秒 |
| 稳定性 | ⭐⭐⭐⭐⭐ 高 | ⭐⭐⭐ 中 |
| 成本 | 调用API费用 | 仅函数费用 |
| 维护成本 | ⭐ 低 | ⭐⭐⭐ 高 |
| 推荐度 | ✅ **强烈推荐** | ⚠️ 可选 |

---

## 🎯 推荐做法

1. **开发测试阶段**: 使用方案A（华为云服务）
   - 快速部署验证
   - 降低复杂度

2. **生产环境**:
   - **优先方案A**：如果API调用量不是特别大
   - **备选方案B**：如果需要离线运行或成本敏感

3. **混合方案**:
   - OCR: 使用华为云OCR（方案A）
   - 视频处理: 使用FFmpeg依赖层（方案B）
   - 理由：OCR频繁调用，视频合并相对较少

---

## 📝 下一步

选择方案后，参考以下文档继续：

- **方案A**: 查看 `HUAWEI_CLOUD_DEPLOYMENT_A.md`
- **方案B**: 查看 `HUAWEI_CLOUD_DEPLOYMENT_B.md`
- **完整部署**: 查看 `SERVERLESS_DEPLOYMENT_GUIDE.md`
