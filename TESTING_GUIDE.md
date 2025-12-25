# Video Vault 测试指南

本文档说明如何在部署到华为云之前进行本地测试，确保所有功能正常工作。

---

## 📋 测试清单

- [ ] 1. 华为云服务连接测试
- [ ] 2. 核心功能本地测试
- [ ] 3. 云函数本地测试
- [ ] 4. 打包脚本测试

---

## 1️⃣ 华为云服务连接测试

**目的**: 验证华为云服务（OBS、OCR、MPC）配置正确且可访问

**测试脚本**: `test_huawei_cloud_services.py`

### 使用方法

```bash
python test_huawei_cloud_services.py
```

### 测试内容

- ✅ OBS存储桶连接测试
- ✅ OCR文字识别服务测试
- ✅ MPC媒体处理服务测试

### 预期输出

```
========================================
  华为云服务连接测试
========================================

[测试1: OBS存储桶]
创建测试文件...
测试文件上传: video-vault-test-<timestamp>.txt
上传成功: video-vault-test-<timestamp>.txt
文件列表:
  - ...
删除成功: video-vault-test-<timestamp>.txt
✅ OBS测试通过

[测试2: OCR服务]
使用测试图片: test_data/test_image.png
识别到的文本块: 10
合并后的文本: Hello World 12345 ...
✅ OCR测试通过

[测试3: MPC服务]
MPC客户端初始化成功
✅ MPC测试通过

========================================
  所有测试通过! ✅
========================================
```

---

## 2️⃣ 核心功能本地测试

**目的**: 测试DLP处理流程的核心逻辑（切片、扫描、脱敏、合并）

**测试脚本**: `local_tests/local_test_pipeline.py`

### 使用方法

```bash
# 使用默认测试视频
python local_tests/local_test_pipeline.py

# 使用指定视频
python local_tests/local_test_pipeline.py path/to/your/video.mp4
```

### 特点

- ✅ **完全本地运行**: 不需要云服务
- ✅ **生成审计日志**: JSON格式记录所有检测
- ✅ **支持自定义视频**: 可以测试任意视频

---

## 3️⃣ 云函数本地测试 ⭐ NEW

**目的**: 在本地模拟华为云FunctionGraph环境，测试云函数逻辑

**测试脚本**: `test_local_handlers.py`

### 使用方法

#### 方法1: 完整流程测试（推荐）

```bash
python test_local_handlers.py test_video.mp4
```

这将测试完整的云函数调用链:
1. Video Slicer Handler - 上传视频并切片
2. DLP Scanner Handler - 扫描一个切片
3. Video Merger Handler - 合并所有切片

#### 方法2: 交互式单独测试

```bash
python test_local_handlers.py
```

然后选择要测试的函数。

### 测试内容

- ✅ **模拟FunctionGraph环境**: Context对象、Logger
- ✅ **真实云服务调用**: 使用实际的OBS、OCR、MPC
- ✅ **完整事件模拟**: OBS触发器、函数调用事件
- ✅ **端到端流程**: 从上传到最终输出

---

## 4️⃣ 打包脚本测试

**目的**: 验证依赖打包脚本能够正确生成部署文件

**测试脚本**: `build_layers.py`

### 使用方法

```bash
python build_layers.py
```

### 重要修复 ⚠️

我已修复了 `build_layers.py` 中的一个关键bug：

**原问题**: 缺少 `esdk-obs-python` 包，导致OBS功能无法使用

**修复**: 在line 36添加了 `"esdk-obs-python==3.23.3"`

---

## 📊 测试对比表

| 测试类型 | 测试范围 | 是否需要云服务 | 建议执行时机 |
|---------|---------|---------------|-------------|
| 华为云服务连接 | OBS、OCR、MPC | ✅ 是 | 配置完成后立即执行 |
| 核心功能本地 | 切片、扫描、合并 | ❌ 否 | 开发过程中频繁执行 |
| 云函数本地 | 3个Handler逻辑 | ✅ 是 | 部署前必须执行 ⭐ |
| 打包脚本 | 依赖打包、配置验证 | ❌ 否 | 部署前执行一次 |

---

## 🚀 推荐测试流程

### 首次部署前

```bash
# 1. 测试云服务连接
python test_huawei_cloud_services.py

# 2. 测试核心功能（本地）
python local_tests/local_test_pipeline.py test_video.mp4

# 3. 测试云函数（真实云服务）⭐ 重要
python test_local_handlers.py test_video.mp4

# 4. 打包部署文件
python build_layers.py
```

### 代码修改后

```bash
# 快速验证核心逻辑
python local_tests/local_test_pipeline.py test_video.mp4

# 验证云函数集成
python test_local_handlers.py test_video.mp4
```

---

## 🔧 常见问题

### 1. "未发现敏感信息"

- 测试视频中确实没有敏感信息
- 使用包含身份证/手机号的测试图片

### 2. "OBS上传/下载失败"

```bash
# 测试OBS连接
python test_huawei_cloud_services.py

# 检查.env配置
cat .env | grep -E "HUAWEI_CLOUD_AK|OBS_BUCKET"
```

### 3. "云函数Handler导入失败"

```bash
# 安装所有依赖
pip install -r requirements.txt

# 确保在项目根目录执行
cd D:\video-vault
python test_local_handlers.py test_video.mp4
```

---

## 📝 测试完成后

测试全部通过后:

1. ✅ 按照 `SERVERLESS_DEPLOYMENT_GUIDE.md` 部署到华为云
2. ✅ 配置环境变量和触发器
3. ✅ 在华为云控制台进行端到端测试

Good luck! 🚀
