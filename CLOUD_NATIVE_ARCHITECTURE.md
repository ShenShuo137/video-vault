# Video Vault 云原生架构说明

## 🎯 架构目标

打造一个**既能本地开发测试，又能无缝部署到华为云Serverless的云原生架构**。

---

## 🏗️ 服务抽象层设计

### 核心思想：双模式架构

```
┌─────────────────────────────────────────────────────┐
│             Video Vault Application                 │
│                                                     │
│  ┌───────────────┐      ┌──────────────────┐      │
│  │  DLP Scanner  │      │  Video Merger    │      │
│  └───────┬───────┘      └────────┬─────────┘      │
│          │                       │                 │
│          ▼                       ▼                 │
│  ┌───────────────┐      ┌──────────────────┐      │
│  │  OCR Service  │      │ Video Processing │      │
│  │   Abstraction │      │    Service       │      │
│  └───────┬───────┘      └────────┬─────────┘      │
│          │                       │                 │
│   ┌──────┴───────┐        ┌──────┴──────┐         │
│   │              │        │             │         │
│   ▼              ▼        ▼             ▼         │
│ ┌─────┐    ┌─────────┐ ┌──────┐  ┌──────────┐   │
│ │Tesse│    │Huawei   │ │FFmpeg│  │Huawei    │   │
│ │ract │    │Cloud OCR│ │      │  │Cloud MPC │   │
│ └─────┘    └─────────┘ └──────┘  └──────────┘   │
│   本地          云端       本地        云端        │
└─────────────────────────────────────────────────────┘
```

---

## 📁 新增文件

### 1. `shared/ocr_service.py` - OCR服务抽象层

**功能：**
- 自动检测运行模式（本地/云端）
- 本地模式：使用Tesseract
- 云端模式：使用华为云OCR API
- 故障降级：云端失败自动降级到本地

**核心代码：**
```python
class OCRService:
    def __init__(self):
        self.use_cloud = not Config.LOCAL_MODE

    def extract_text(self, image):
        if self.use_cloud:
            return self._huawei_ocr(image)  # 华为云OCR
        else:
            return self._tesseract_ocr(image)  # 本地Tesseract
```

**优势：**
- ✅ 统一接口，业务代码无需改动
- ✅ 配置驱动，切换环境只需改.env
- ✅ 云端准确率更高（训练数据更多）
- ✅ 自动故障恢复

### 2. `shared/video_processing_service.py` - 视频处理服务抽象层

**功能：**
- 本地模式：FFmpeg > OpenCV
- 云端模式：华为云MPC（Media Processing Center）
- 智能降级：云端失败降级到本地

**核心代码：**
```python
class VideoProcessingService:
    def __init__(self):
        self.use_cloud = not Config.LOCAL_MODE

    def merge_videos(self, slice_files, output_path):
        if self.use_cloud:
            return self._huawei_mpc_merge(...)  # 华为云MPC
        else:
            return self._local_merge(...)  # FFmpeg/OpenCV
```

**优势：**
- ✅ FFmpeg在云函数中难以打包（50MB+）
- ✅ MPC是华为云原生服务，更稳定
- ✅ 支持大文件和高并发
- ✅ 本地开发不受影响

---

## ⚙️ 配置切换

### 本地开发模式 (.env)

```env
# 本地测试模式
LOCAL_MODE=true

# 不需要配置云服务
# HUAWEI_CLOUD_AK=
# HUAWEI_CLOUD_SK=
```

**行为：**
- OCR：使用本地Tesseract
- 视频合并：使用FFmpeg或OpenCV
- 存储：本地文件系统
- 数据库：可选（不配置时使用内存）

### 云端生产模式 (.env)

```env
# 云端生产模式
LOCAL_MODE=false

# 华为云配置
HUAWEI_CLOUD_AK=your_access_key
HUAWEI_CLOUD_SK=your_secret_key
HUAWEI_CLOUD_REGION=cn-north-4

# OBS配置
OBS_BUCKET_NAME=video-vault-storage

# 数据库配置
DB_HOST=rds-xxx.huaweicloud.com
DB_PASSWORD=xxx
```

**行为：**
- OCR：使用华为云OCR API
- 视频合并：使用华为云MPC
- 存储：华为云OBS
- 数据库：华为云RDS MySQL

---

## 🔄 迁移路径

### 阶段1：当前（本地开发）✅
```
开发机 → Tesseract + FFmpeg → 本地文件
```

### 阶段2：混合模式
```
开发机 → 华为云OCR API → 本地文件
         ↓
       验证云端服务可用性
```

### 阶段3：完全云端
```
FunctionGraph → 华为云OCR + MPC → OBS + RDS
```

---

## 🌟 华为云服务对比

### OCR服务

| 对比项 | 本地Tesseract | 华为云OCR |
|-------|--------------|-----------|
| 准确率 | 70-80% | 95%+ |
| 速度 | CPU密集，慢 | API调用，快 |
| 支持语言 | 需下载语言包 | 100+语言内置 |
| 专业识别 | 无 | 身份证/银行卡等 |
| 部署难度 | 高（需打包） | 低（API调用） |
| 成本 | 免费 | 0.01元/次 |

### 视频处理

| 对比项 | FFmpeg | 华为云MPC |
|-------|--------|-----------|
| 部署难度 | 高（50MB+） | 低（API调用） |
| 并发能力 | 受函数限制 | 自动扩展 |
| 功能 | 基础合并 | 转码/水印/剪辑 |
| 稳定性 | 需自己维护 | 官方保证 |
| 成本 | 免费 | 按转码时长 |

---

## 💰 成本估算

### 场景：每天处理10个视频

**假设：**
- 每个视频：10分钟
- 关键帧：600帧（每秒1帧）
- OCR识别：600次/视频
- 视频合并：10次/天

**月度成本：**

| 服务 | 用量 | 单价 | 月成本 |
|-----|------|------|-------|
| 华为云OCR | 10视频×600次×30天=180k次 | 0.01元/次 | 1800元 |
| 华为云MPC | 10分钟×10视频×30天=3000分钟 | 0.05元/分钟 | 150元 |
| OBS存储 | 100GB | 0.1元/GB/月 | 10元 |
| RDS数据库 | 1核2GB | 按需 | 200元 |
| **总计** | - | - | **~2160元/月** |

**优化建议：**
1. 降低关键帧提取频率（2秒1帧）→ 节省50% OCR成本
2. 使用OSS归档存储 → 节省80% 存储成本
3. 批量处理 → 提高效率

---

## 🚀 部署步骤

### Step 1: 开通华为云服务

1. **OCR服务**
   - 控制台：服务列表 → OCR → 开通服务
   - 获取免费额度：1000次/月
   - 记录项目ID

2. **MPC服务**（可选，后期添加）
   - 控制台：服务列表 → MPC → 开通服务
   - 创建转码模板

3. **获取AK/SK**
   - 我的凭证 → 访问密钥 → 新增访问密钥
   - 保存AccessKey和SecretKey

### Step 2: 配置环境变量

编辑 `.env`:
```env
LOCAL_MODE=false
HUAWEI_CLOUD_AK=ABCD...
HUAWEI_CLOUD_SK=xyz...
HUAWEI_CLOUD_REGION=cn-north-4
```

### Step 3: 测试云端服务

```bash
# 运行测试
python local_tests/local_test_pipeline.py
```

**预期输出：**
```
OCR模式: 华为云OCR
视频处理模式: 本地FFmpeg  # MPC可选，暂时用本地
...
```

### Step 4: 封装FunctionGraph函数

创建 `functions/video_slicer/index.py`:
```python
from shared.video_slicer import VideoSlicer
from shared.obs_helper import OBSHelper

def handler(event, context):
    # 从OBS事件获取视频
    obs_key = event['obs']['object']['key']

    # 下载并切片
    obs = OBSHelper()
    local_path = f'/tmp/{obs_key}'
    obs.download_file(obs_key, local_path)

    slicer = VideoSlicer()
    slices = slicer.slice_video(local_path, '/tmp/slices')

    # 上传切片
    for slice_file in slices:
        obs.upload_file(slice_file, f'slices/{...}')

    return {'status': 'success'}
```

---

## ✨ 架构优势

### 1. 开发体验好
- ✅ 本地开发不依赖云服务
- ✅ 快速迭代和调试
- ✅ 离线也能工作

### 2. 生产质量高
- ✅ 使用云原生服务
- ✅ 准确率和稳定性更高
- ✅ 自动扩展和容灾

### 3. 迁移成本低
- ✅ 只需修改配置文件
- ✅ 业务代码无需改动
- ✅ 渐进式迁移

### 4. 成本可控
- ✅ 按需付费
- ✅ 有免费额度
- ✅ 可灵活优化

---

## 🎯 下一步

### 立即可做
1. ✅ 配置华为云AK/SK
2. ✅ 测试华为云OCR服务
3. 🔄 验证识别准确率

### 近期计划
1. 封装FunctionGraph函数入口
2. 配置OBS触发器
3. 部署到华为云
4. 完整流程测试

### 可选增强
1. 添加华为云MPC支持
2. 实现智能降级策略
3. 添加性能监控
4. 成本优化

---

**总结：** 现在的架构既支持本地开发，又能无缝部署到华为云，是真正的云原生设计！🎉
