# 华为云服务配置指南

## 🎯 目标

配置华为云OCR和MPC服务，实现真正的云原生视频处理。

---

## 📋 准备工作

### 1. 注册华为云账号
- 访问: https://www.huaweicloud.com
- 注册并完成实名认证
- 领取新用户优惠券（如有）

### 2. 获取访问密钥 (AK/SK)

**步骤：**
1. 登录华为云控制台
2. 右上角点击用户名 → "我的凭证"
3. 左侧菜单 → "访问密钥"
4. 点击"新增访问密钥"
5. 下载密钥文件（csv格式）

**密钥说明：**
- AccessKey (AK): 访问密钥ID，类似用户名
- SecretKey (SK): 秘密访问密钥，类似密码
- ⚠️ 妥善保管，不要泄露！

---

## 🔧 服务配置

### 步骤1: 开通OCR服务

**1.1 进入OCR服务**
```
控制台 → 产品与服务 → AI → 文字识别 OCR
```

**1.2 开通服务**
- 点击"立即开通"
- 同意服务协议
- 开通成功

**1.3 查看免费额度**
- 通用文字识别：1000次/月 免费
- 对于作业演示完全够用！

**1.4 记录项目ID**
```
控制台 → 我的凭证 → API凭证 → 项目列表
```
找到你的区域（如cn-north-4）对应的项目ID

### 步骤2: 开通MPC服务

**2.1 进入MPC服务**
```
控制台 → 产品与服务 → 视频 → 媒体处理 MPC
```

**2.2 开通服务**
- 点击"立即使用"
- 同意服务协议
- 开通成功

**2.3 了解计费**
| 功能 | 规格 | 单价 |
|-----|------|------|
| 视频拼接 | H.264, 1080P | 0.0654元/分钟 |
| 视频转码 | H.264, 1080P | 0.0654元/分钟 |

**估算（10分钟测试视频）：**
- 1次拼接：10分钟 × 0.0654元 = 0.654元
- 10次测试：≈ 6.5元
- **非常便宜！**

### 步骤3: 创建OBS存储桶

**3.1 进入OBS服务**
```
控制台 → 产品与服务 → 存储 → 对象存储服务 OBS
```

**3.2 创建存储桶**
- 点击"创建桶"
- 桶名称：`video-vault-storage`（唯一，不能重复）
- 区域：cn-north-4（华北-北京四）
- 存储类别：标准存储
- 桶策略：私有
- 点击"立即创建"

**3.3 创建目录结构**

进入桶 → 创建以下文件夹：
```
video-vault-storage/
├── videos/          # 原始视频
├── slices/          # 视频切片
├── processed/       # 处理后的切片
├── output/          # 最终输出
└── temp/            # 临时文件
    ├── slices/      # MPC用的临时切片
    └── output/      # MPC输出临时文件
```

**3.4 查看Endpoint**
- 在桶概览页面找到"Endpoint"
- 格式：`https://video-vault-storage.obs.cn-north-4.myhuaweicloud.com`
- 记录下来（虽然代码会自动构建）

---

## ⚙️ 配置项目

### 编辑 `.env` 文件

```env
# ========== 运行模式 ==========
# true=本地测试, false=云端生产
LOCAL_MODE=false

# ========== 华为云凭证 ==========
HUAWEI_CLOUD_AK=ABCDEFGHIJ1234567890      # 替换为你的AK
HUAWEI_CLOUD_SK=abcd1234efgh5678ijkl9012  # 替换为你的SK
HUAWEI_CLOUD_REGION=cn-north-4            # 区域

# ========== OBS配置 ==========
OBS_BUCKET_NAME=video-vault-storage       # 你创建的桶名
OBS_ENDPOINT=obs.cn-north-4.myhuaweicloud.com

# ========== OCR配置 ==========
OCR_ENDPOINT=https://ocr.cn-north-4.myhuaweicloud.com
OCR_PROJECT_ID=your_project_id_here       # 替换为你的项目ID

# ========== 数据库配置（可选，暂时不需要）==========
# 本地测试可以不配置数据库
# DB_HOST=localhost
# DB_PORT=3306
# DB_NAME=video_vault
# DB_USER=root
# DB_PASSWORD=

# ========== AI Agent配置（可选）==========
# 如果要测试AI Agent，需要配置
# LLM_API_KEY=your_openai_key
# LLM_API_BASE=https://api.openai.com/v1
# LLM_MODEL=gpt-4

# ========== DLP配置 ==========
SLICE_DURATION=60                          # 视频切片时长(秒)
OCR_CONFIDENCE_THRESHOLD=0.6               # OCR置信度阈值
BLUR_INTENSITY=51                          # 高斯模糊强度
```

---

## 🧪 测试配置

### 步骤1: 安装依赖

```bash
# 安装华为云SDK
pip install huaweicloudsdkmpc

# 或者全部重装
pip install -r requirements.txt
```

### 步骤2: 测试OCR服务

创建测试脚本 `test_huawei_ocr.py`:

```python
from shared.ocr_service import OCRService
import cv2

# 读取测试图像（确保有文字）
image = cv2.imread('test_image.jpg')

# 测试OCR
ocr = OCRService()
results = ocr.extract_text(image)

print(f"识别到 {len(results)} 个文本块:")
for i, result in enumerate(results):
    print(f"{i+1}. {result['text']} (置信度: {result['confidence']:.2f})")
```

运行：
```bash
python test_huawei_ocr.py
```

**预期输出：**
```
OCR模式: 华为云OCR
识别到 5 个文本块:
1. Hello World (置信度: 0.98)
2. 测试文本 (置信度: 0.95)
...
```

### 步骤3: 测试MPC视频拼接

```bash
# 生成测试视频
python local_tests/create_test_video.py

# 运行完整流程（会使用华为云服务）
python local_tests/local_test_pipeline.py
```

**预期输出：**
```
============================================================
Video Vault DLP 处理流水线已初始化
运行模式: 云端生产
============================================================
OCR模式: 华为云OCR
视频处理模式: 华为云MPC

🎬 开始处理视频: test_video.mp4

📹 阶段1: 视频切片
✅ 切片完成: 1 个切片

🔍 阶段2: DLP扫描与脱敏处理
扫描帧 0 (时间=0.00s)...
[调用华为云OCR API...]
⚠️  发现 3 个敏感信息!
✅ DLP扫描完成

🎞️  阶段3: 合并处理后的视频
使用华为云MPC合并 1 个切片...
Step 1: 上传切片到OBS...
Step 2: 创建MPC拼接任务...
Step 3: 等待任务完成...
Step 4: 下载结果...
Step 5: 清理临时文件...
✓ MPC合并完成

✅ 处理完成!
```

---

## 🐛 常见问题

### Q1: OCR报错 "SDK.InvalidCredential"

**原因：** AK/SK配置错误

**解决：**
1. 检查.env中的AK/SK是否正确
2. 确保没有多余空格
3. 确保SK没有泄露（如果泄露了，重新生成）

### Q2: MPC报错 "bucket not found"

**原因：** OBS桶不存在或名称错误

**解决：**
1. 检查桶名是否正确
2. 确保桶在同一区域（cn-north-4）
3. 确保桶是私有的，不是公共读

### Q3: 成本担心

**解决：**
1. 开发阶段用本地模式（LOCAL_MODE=true）
2. 只在最终演示时用云端模式
3. 测试用短视频（<1分钟）
4. 及时删除OBS中的临时文件

### Q4: OCR识别不准确

**解决：**
1. 确保视频中的文字清晰
2. 降低OCR_CONFIDENCE_THRESHOLD（但会有误报）
3. 使用华为云OCR专业版API（按需）

---

## 💰 成本控制

### 免费额度

| 服务 | 免费额度 | 说明 |
|-----|---------|------|
| OCR | 1000次/月 | 通用文字识别 |
| OBS | 5GB | 标准存储 |

### 付费部分

| 服务 | 用量估算 | 成本 |
|-----|---------|-----|
| MPC视频拼接 | 10个视频 × 10分钟 | ≈6.5元 |
| OBS流量 | 上传/下载100次 × 100MB | ≈0.5元 |
| **总计** | **作业演示** | **<10元** |

### 节省建议

1. **本地开发用本地模式**
   ```env
   LOCAL_MODE=true
   ```

2. **最终演示才用云端**
   ```env
   LOCAL_MODE=false
   ```

3. **用完及时清理OBS临时文件**

4. **使用短视频测试**（10-30秒）

---

## ✅ 配置检查清单

- [ ] 华为云账号已注册
- [ ] AK/SK已获取并配置到.env
- [ ] OCR服务已开通
- [ ] MPC服务已开通
- [ ] OBS存储桶已创建
- [ ] 项目ID已配置
- [ ] 依赖已安装（huaweicloudsdkmpc）
- [ ] 测试OCR成功
- [ ] 测试MPC视频拼接成功

---

## 🚀 下一步

配置完成后，你就可以：

1. ✅ 本地开发时用Tesseract和FFmpeg
2. ✅ 部署演示时用华为云OCR和MPC
3. ✅ 一键切换，无需改代码
4. ✅ 展示真正的云原生架构

**祝开发顺利！** 🎉
