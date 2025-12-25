# Video Vault 华为云Serverless部署完整指南

> 完全基于华为云FunctionGraph + OBS的Serverless架构部署方案
>
> **更新日期**: 2024年 | **架构版本**: Serverless v2.0

---

## 📑 目录

1. [架构概览](#1-架构概览)
2. [前置准备](#2-前置准备)
3. [环境检查](#3-环境检查)
4. [打包依赖和代码](#4-打包依赖和代码)
5. [创建OBS存储桶](#5-创建obs存储桶)
6. [上传依赖层](#6-上传依赖层)
7. [创建云函数](#7-创建云函数)
8. [配置前端](#8-配置前端)
9. [测试验证](#9-测试验证)
10. [监控和优化](#10-监控和优化)
11. [常见问题](#11-常见问题)

---

## 1. 架构概览

### 1.1 完全Serverless架构

```
┌─────────────┐
│   前端应用   │ (Vue 3 + Vite)
│ (本地/托管)  │
└──────┬──────┘
       │
       │ ① 直接上传视频
       ▼
┌─────────────────────────────────────┐
│         OBS 对象存储                 │
│  ┌──────────────────────────────┐   │
│  │ uploads/   (上传目录)         │◄──┤ 前端直接读写
│  │ slices/    (切片临时)         │   │
│  │ processed/ (处理后切片)        │   │
│  │ outputs/   (最终视频)         │   │
│  │ logs/      (审计日志JSON)     │   │
│  └──────────────────────────────┘   │
└──────┬──────────────────────────────┘
       │
       │ ② OBS事件触发
       ▼
┌────────────────────────────────────┐
│   FunctionGraph 云函数工作流       │
│                                    │
│  ┌─────────────────────┐           │
│  │ video_slicer       │ (1实例)   │
│  │ 视频切片            │           │
│  └──────────┬──────────┘           │
│             │                      │
│             │ ③ 并行调用           │
│             ▼                      │
│  ┌─────────────────────┐           │
│  │ dlp_scanner  (N实例)│           │
│  │ DLP扫描+脱敏         │           │
│  └──────────┬──────────┘           │
│             │                      │
│             │ ④ 完成后调用         │
│             ▼                      │
│  ┌─────────────────────┐           │
│  │ video_merger       │ (1实例)   │
│  │ 视频合并            │           │
│  └─────────────────────┘           │
│                                    │
│  ┌─────────────────────┐           │
│  │ ai_agent (HTTP)     │◄──────── 前端HTTP调用
│  │ AI对话助手          │           │
│  └─────────────────────┘           │
└────────────────────────────────────┘
```

### 1.2 核心特性

✅ **完全无服务器** - 无需管理服务器，按使用量付费
✅ **数据库可选** - 数据存储在OBS，MySQL仅作为可选备份
✅ **自动伸缩** - 自动处理并发，支持400个函数实例
✅ **事件驱动** - OBS触发自动处理，无需手动启动
✅ **前端直连OBS** - 前端直接读写OBS，无需后端API

### 1.3 资源配额评估

**你的函数工作流配额**: 400个实例

**推荐配置**:
- `video-vault-slicer`: 最大10实例
- `video-vault-dlp`: 最大350实例（核心并发）
- `video-vault-merger`: 最大10实例
- `video-vault-ai-agent`: 最大30实例

**处理能力**:
- 单视频最大支持: 350个切片 = 350分钟（约6小时）
- 并发视频数: 理论可同时处理10+个视频

---

## 2. 前置准备

### 2.1 华为云账号

✅ **必须开通的服务**:
1. **FunctionGraph** (函数工作流) - 免费，仅按使用量付费
2. **OBS** (对象存储服务) - 首年有免费额度
3. **OCR** (文字识别) - 按调用次数付费
4. **APIG** (API网关) - 免费（AI Agent需要）

⚠️ **可选服务**:
- **RDS MySQL** (关系型数据库) - 作为审计日志备份（本部署方案不需要）
- **MPC** (媒体处理) - 视频转码（不需要，使用FFmpeg）

### 2.2 获取访问密钥

1. 登录华为云控制台
2. 点击右上角用户名 → **我的凭证**
3. 左侧菜单 → **访问密钥**
4. 点击 **新增访问密钥**
5. 输入登录密码和验证码
6. 下载 `credentials.csv` 文件

**保存以下信息**:
```
Access Key Id (AK): HPUACBZNVJEWFWDF8ZEW
Secret Access Key (SK): PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu
```

⚠️ **安全提示**:
- 不要将AK/SK提交到Git仓库
- 不要分享给他人
- 定期轮换密钥

### 2.3 获取项目ID

1. 华为云控制台 → 右上角用户名 → **我的凭证**
2. 左侧菜单 → **API凭证**
3. 找到你的区域（如 `华北-北京四 cn-north-4`）
4. 记录对应的 **项目ID**

示例:
```
区域: cn-north-4
项目ID: 96c5e3fa586c486e977707f516a95e4d
```

### 2.4 开通OCR服务

1. 华为云控制台 → 搜索 **文字识别 OCR**
2. 点击 **开通服务**
3. 选择 **通用文字识别** (免费额度：1000次/月)
4. 同意协议，开通

### 2.5 本地环境准备

**Python环境**:
- ✅ **必须**: Python 3.9（与华为云运行时一致）
- ❌ 不推荐: Python 3.10+ 或 3.8-（会导致依赖包不兼容）

**安装Python 3.9**:
```bash
# Windows
https://www.python.org/downloads/release/python-3913/
# 下载并安装，记得勾选"Add to PATH"

# Linux
sudo apt update
sudo apt install python3.9 python3.9-venv

# macOS
brew install python@3.9
```

**验证版本**:
```bash
python3.9 --version
# 输出: Python 3.9.13 (或 3.9.x)
```

---

## 3. 环境检查

### 3.1 检查你的 `.env` 配置

项目根目录的 `.env` 文件应该已配置：

```bash
# ✅ 华为云配置（必填）
HUAWEI_CLOUD_AK=HPUACBZNVJEWFWDF8ZEW
HUAWEI_CLOUD_SK=PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu
HUAWEI_CLOUD_REGION=cn-north-4

# ✅ OBS对象存储配置（必填）
OBS_BUCKET_NAME=video-vault-storage
OBS_ENDPOINT=obs.cn-north-4.myhuaweicloud.com

# ✅ RDS数据库配置（可选，已注释）
# DB_HOST=your_rds_host
# DB_PORT=3306
# DB_NAME=video_vault
# DB_USER=root
# DB_PASSWORD=your_password

# ✅ AI大模型API配置（必填，AI功能需要）
LLM_API_KEY=sk-B2WnTcrxS5MzRvNngtoy9NtSDq4Yt7toOVF2E02WA8ubf8pG
LLM_API_BASE=https://api.chatanywhere.tech/v1
LLM_MODEL=gpt-4o-mini

# ✅ 华为云OCR服务配置（必填）
OCR_ENDPOINT=https://ocr.cn-north-4.myhuaweicloud.com
OCR_PROJECT_ID=96c5e3fa586c486e977707f516a95e4d
OCR_CONFIDENCE_THRESHOLD=0.6

# ✅ MPC配置（可选，不使用）
MPC_ENDPOINT=https://mpc.cn-north-4.myhuaweicloud.com
MPC_PROJECT_ID=96c5e3fa586c486e977707f516a95e4d
```

**检查清单**:
- ✅ HUAWEI_CLOUD_AK 和 SK 已填写
- ✅ OBS_BUCKET_NAME 已填写
- ✅ LLM_API_KEY 已填写（用于AI Agent）
- ✅ OCR_PROJECT_ID 已填写
- ⚠️ 数据库配置已注释（不需要）

### 3.2 验证配置有效性

运行以下脚本验证配置：

```bash
python -c "
from dotenv import load_dotenv
import os

load_dotenv()

print('华为云配置:')
print(f'  AK: {os.getenv(\"HUAWEI_CLOUD_AK\")[:8]}***')
print(f'  Region: {os.getenv(\"HUAWEI_CLOUD_REGION\")}')
print(f'\nOBS配置:')
print(f'  Bucket: {os.getenv(\"OBS_BUCKET_NAME\")}')
print(f'\nAI配置:')
print(f'  Model: {os.getenv(\"LLM_MODEL\")}')
print(f'  API: {os.getenv(\"LLM_API_BASE\")}')
print('\n✅ 配置检查完成')
"
```

---

## 4. 打包依赖和代码

### 4.1 使用自动化打包脚本

项目已包含自动化打包脚本 `build_layers.py`，一键完成所有打包工作。

**执行打包**:

```bash
# 确保使用 Python 3.9
python3.9 build_layers.py
```

**打包过程** (约5-10分钟):
```
╔══════════════════════════════════════════════════════════╗
║          Video Vault 依赖层打包工具                      ║
║          Dependency Layer Packaging Tool                  ║
╚══════════════════════════════════════════════════════════╝

============================================================
  1. 创建Python依赖层
============================================================

检测Python版本...
✅ 当前Python版本: 3.9.13

安装Python依赖（最新稳定版）...
安装普通依赖包...
安装华为云SDK（禁用依赖检查）...
复制项目代码...
清理不必要的文件...
打包依赖层...

✅ 依赖层打包完成: layers/python-deps.zip
   大小: 68.45 MB

============================================================
  2. 打包函数代码
============================================================

✅ video_slicer.zip: 3.12 KB
✅ dlp_scanner.zip: 4.87 KB
✅ video_merger.zip: 2.91 KB
✅ ai_agent.zip: 12.34 KB

============================================================
  3. 验证环境配置
============================================================

✅ HUAWEI_CLOUD_AK: HPUA****8ZEW
✅ HUAWEI_CLOUD_SK: PbWh****XkHu
✅ OBS_BUCKET_NAME: video-vault-storage
✅ LLM_API_KEY: sk-B****f8pG
✅ LLM_MODEL: gpt-4o-mini

============================================================
  部署文件已准备好
============================================================

📦 依赖层:
   layers/python-deps.zip

📄 函数代码:
   deploy/video_slicer.zip (3.12 KB)
   deploy/dlp_scanner.zip (4.87 KB)
   deploy/video_merger.zip (2.91 KB)
   deploy/ai_agent.zip (12.34 KB)

📚 下一步:
   1. 登录华为云控制台
   2. 上传依赖层: layers/python-deps.zip
   3. 创建4个函数并上传代码
   4. 配置环境变量和触发器
   5. 测试部署

✅ 打包完成!
```

### 4.2 确认生成的文件

检查项目目录：

```
video-vault/
├── layers/
│   └── python-deps.zip         # ~68MB（依赖层）
└── deploy/
    ├── video_slicer.zip        # ~3KB
    ├── dlp_scanner.zip         # ~5KB
    ├── video_merger.zip        # ~3KB
    └── ai_agent.zip            # ~12KB
```

**依赖层包含**:
- 华为云SDK (obs, ocr, functiongraph, mpc)
- 视频处理库 (opencv-python, ffmpeg-python, Pillow, numpy)
- OCR库 (pytesseract)
- 数据库库 (PyMySQL)
- Web框架 (Flask, Flask-CORS, requests)
- AI库 (openai)
- 工具库 (python-dotenv, colorlog, tqdm等)
- 项目共享代码 (shared/ 目录)

### 4.3 如果打包失败

**常见问题**:

1. **Python版本不是3.9**
   ```bash
   ⚠️  警告: 当前Python版本为 3.11.x
   建议使用Python 3.9打包以避免兼容性问题
   ```
   **解决**: 安装Python 3.9，使用 `python3.9 build_layers.py`

2. **依赖层超过100MB**
   ```bash
   ⚠️  警告: 文件大小超过100MB限制!
   ```
   **解决**: 脚本已自动清理，如果还超过，联系技术支持

3. **网络超时**
   ```bash
   ❌ 普通包安装失败: Connection timeout
   ```
   **解决**: 使用国内镜像（脚本已配置清华镜像）

---

## 5. 创建OBS存储桶

### 5.1 登录OBS控制台

1. 华为云控制台 → 搜索 **对象存储服务 OBS**
2. 点击 **创建桶**

### 5.2 创建存储桶

填写配置：

```
桶名称: video-vault-storage
区域: 华北-北京四 (cn-north-4)  【必须与函数同区域】
数据冗余存储策略: 单AZ存储
存储类别: 标准存储
桶策略: 私有
默认加密: 不启用
多版本控制: 不启用
日志记录: 不启用
```

点击 **立即创建**

### 5.3 配置CORS（重要！）

前端需要直接访问OBS，必须配置CORS。

1. 进入 `video-vault-storage` 桶
2. 左侧菜单 → **访问权限配置** → **CORS规则**
3. 点击 **创建**
4. 填写配置：

```
规则ID: frontend-access
允许的来源(Allowed Origin): *
允许的方法(Allowed Method): ✅ GET ✅ PUT ✅ POST ✅ DELETE ✅ HEAD
允许的头部(Allowed Header): *
暴露的头部(Expose Header): ETag, x-amz-request-id, x-amz-id-2
缓存时间(Max Age): 3600
```

5. 点击 **确定**

### 5.4 创建目录结构

**方式1: 使用OBS Browser工具**

1. 下载并安装 [OBS Browser+](https://support.huaweicloud.com/browsertg-obs/obs_03_1003.html)
2. 登录 (使用AK/SK)
3. 进入 `video-vault-storage`
4. 创建以下文件夹：
   - `uploads/` (上传目录)
   - `slices/` (切片临时目录)
   - `processed/` (处理后切片)
   - `outputs/` (最终输出)
   - `logs/` (审计日志)

**方式2: 控制台手动创建**

1. OBS控制台 → 进入 `video-vault-storage`
2. 点击 **新建文件夹**
3. 依次创建上述5个文件夹

**方式3: 自动创建（首次上传时）**

实际上这些目录会在首次上传文件时自动创建，无需手动创建。

### 5.5 验证OBS配置

运行测试脚本：

```bash
python -c "
from shared.obs_helper import OBSHelper

obs = OBSHelper()
print('测试上传文件...')
with open('test.txt', 'w') as f:
    f.write('hello')
obs.upload_file('test.txt', 'uploads/test.txt')
print('✅ OBS配置正确')
"
```

---

## 6. 上传依赖层

### 6.1 登录FunctionGraph控制台

1. 华为云控制台 → 搜索 **函数工作流 FunctionGraph**
2. 选择区域: **华北-北京四 (cn-north-4)**

### 6.2 上传依赖层

1. 左侧菜单 → **依赖包管理**
2. 点击 **创建依赖包**
3. 填写配置：

```
依赖包名称: video-vault-python-deps
运行时: Python 3.9
上传方式: 本地ZIP
依赖包文件: 选择 layers/python-deps.zip
描述: Video Vault Python依赖层（包含所有SDK和项目代码）
```

4. 点击 **确定**
5. 等待上传完成（约1-2分钟，取决于网络）

**上传进度**:
```
正在上传... 35% (24MB / 68MB)
正在上传... 70% (48MB / 68MB)
正在上传... 100% (68MB / 68MB)
✅ 上传成功
```

### 6.3 记录依赖层版本

上传成功后，记录依赖层信息：

```
名称: video-vault-python-deps
版本: 1
运行时: Python 3.9
大小: 68.45 MB
```

---

## 7. 创建云函数

我们需要创建4个云函数，下面是详细步骤。

---

### 7.1 函数1: video-vault-slicer (视频切片)

#### 7.1.1 作用说明

- 接收OBS上传事件（用户上传视频触发）
- 下载视频到 `/tmp/`
- 切片为多个小段（默认60秒/片）
- 上传切片到OBS `slices/` 目录
- 并行调用DLP扫描函数处理每个切片

#### 7.1.2 创建函数

1. FunctionGraph控制台 → **函数** → **创建函数**
2. 选择 **从头开始创建**
3. 填写基本信息：

```
函数名称: video-vault-slicer
所属应用: （新建应用）video-vault
委托名称: （暂不选择）
运行时: Python 3.9
函数类型: 事件函数
```

4. 代码配置：

```
代码上传方式: 本地ZIP
选择ZIP文件: deploy/video_slicer.zip
函数执行入口: video_slicer_handler.handler
```

5. 高级配置：

```
内存: 2048 MB
超时时间: 900 秒
实例数配置:
  - 最小实例数: 0
  - 最大实例数: 10
```

6. 依赖层配置：
   - 点击 **添加依赖层**
   - 选择 `video-vault-python-deps` 版本1

7. 环境变量：

点击 **环境变量** 标签，添加：

```
HUAWEI_CLOUD_AK=HPUACBZNVJEWFWDF8ZEW
HUAWEI_CLOUD_SK=PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu
HUAWEI_CLOUD_REGION=cn-north-4
OBS_BUCKET_NAME=video-vault-storage
OBS_ENDPOINT=obs.cn-north-4.myhuaweicloud.com
SLICE_DURATION=60
DLP_SCANNER_FUNCTION_URN=【暂时留空，后面回填】
```

8. 点击 **创建函数**

#### 7.1.3 记录函数URN

创建成功后，进入函数详情页，复制函数URN：

```
urn:fss:cn-north-4:xxxxx:function:default:video-vault-slicer:latest
```

**重要**: 保存这个URN，后面配置触发器时需要。

---

### 7.2 函数2: video-vault-dlp (DLP扫描+脱敏)

#### 7.2.1 作用说明

- 接收视频切片信息（由slicer函数调用）
- 下载切片到 `/tmp/`
- 提取关键帧进行OCR扫描
- 检测敏感信息（身份证、密钥、密码等）
- 对敏感帧进行模糊处理
- 上传处理后的切片到OBS `processed/` 目录
- 保存审计日志到OBS `logs/` 目录
- 检查是否所有切片完成，触发合并函数

#### 7.2.2 创建函数

1. FunctionGraph控制台 → **函数** → **创建函数**
2. 选择 **从头开始创建**
3. 基本信息：

```
函数名称: video-vault-dlp
所属应用: video-vault
运行时: Python 3.9
函数类型: 事件函数
```

4. 代码配置：

```
代码上传方式: 本地ZIP
选择ZIP文件: deploy/dlp_scanner.zip
函数执行入口: dlp_scanner_handler.handler
```

5. 高级配置：

```
内存: 2048 MB
超时时间: 900 秒
实例数配置:
  - 最小实例数: 0
  - 最大实例数: 350  【重要：支持大规模并行】
```

6. 依赖层：
   - 添加 `video-vault-python-deps` 版本1

7. 环境变量：

```
HUAWEI_CLOUD_AK=HPUACBZNVJEWFWDF8ZEW
HUAWEI_CLOUD_SK=PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu
HUAWEI_CLOUD_REGION=cn-north-4
OBS_BUCKET_NAME=video-vault-storage
OBS_ENDPOINT=obs.cn-north-4.myhuaweicloud.com
OCR_ENDPOINT=https://ocr.cn-north-4.myhuaweicloud.com
OCR_PROJECT_ID=96c5e3fa586c486e977707f516a95e4d
OCR_CONFIDENCE_THRESHOLD=0.6
BLUR_INTENSITY=51
VIDEO_MERGER_FUNCTION_URN=【暂时留空，后面回填】
```

8. 点击 **创建函数**

#### 7.2.3 记录函数URN并回填

创建成功后：

1. 复制本函数URN:
   ```
   urn:fss:cn-north-4:xxxxx:function:default:video-vault-dlp:latest
   ```

2. **重要**: 回填到函数1的环境变量
   - 打开 `video-vault-slicer` 函数
   - 点击 **配置** → **环境变量**
   - 编辑 `DLP_SCANNER_FUNCTION_URN`，填入上面的URN
   - 保存

---

### 7.3 函数3: video-vault-merger (视频合并)

#### 7.3.1 作用说明

- 接收合并任务（由dlp函数调用）
- 下载所有处理后的切片到 `/tmp/`
- 使用FFmpeg合并为完整视频
- 上传到OBS `outputs/` 目录
- 清理临时文件

#### 7.3.2 创建函数

1. FunctionGraph控制台 → **函数** → **创建函数**
2. 基本信息：

```
函数名称: video-vault-merger
所属应用: video-vault
运行时: Python 3.9
函数类型: 事件函数
```

3. 代码配置：

```
代码上传方式: 本地ZIP
选择ZIP文件: deploy/video_merger.zip
函数执行入口: video_merger_handler.handler
```

4. 高级配置：

```
内存: 2048 MB
超时时间: 900 秒
实例数配置:
  - 最小实例数: 0
  - 最大实例数: 10
```

5. 依赖层：
   - 添加 `video-vault-python-deps` 版本1

6. 环境变量：

```
HUAWEI_CLOUD_AK=HPUACBZNVJEWFWDF8ZEW
HUAWEI_CLOUD_SK=PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu
HUAWEI_CLOUD_REGION=cn-north-4
OBS_BUCKET_NAME=video-vault-storage
OBS_ENDPOINT=obs.cn-north-4.myhuaweicloud.com
```

7. 点击 **创建函数**

#### 7.3.3 记录函数URN并回填

1. 复制本函数URN:
   ```
   urn:fss:cn-north-4:xxxxx:function:default:video-vault-merger:latest
   ```

2. **重要**: 回填到函数2的环境变量
   - 打开 `video-vault-dlp` 函数
   - 点击 **配置** → **环境变量**
   - 编辑 `VIDEO_MERGER_FUNCTION_URN`，填入上面的URN
   - 保存

---

### 7.4 函数4: video-vault-ai-agent (AI对话助手)

#### 7.4.1 作用说明

- 接收前端HTTP请求
- 使用OpenAI API (ChatAnywhere) 提供AI对话
- 从OBS读取审计日志和视频信息
- 支持查询敏感信息、生成报告等功能

#### 7.4.2 创建函数

1. FunctionGraph控制台 → **函数** → **创建函数**
2. 基本信息：

```
函数名称: video-vault-ai-agent
所属应用: video-vault
运行时: Python 3.9
函数类型: 事件函数  【注意：不是HTTP函数】
```

3. 代码配置：

```
代码上传方式: 本地ZIP
选择ZIP文件: deploy/ai_agent.zip
函数执行入口: ai_agent_handler.handler
```

4. 高级配置：

```
内存: 1024 MB
超时时间: 300 秒
实例数配置:
  - 最小实例数: 0
  - 最大实例数: 30
```

5. 依赖层：
   - 添加 `video-vault-python-deps` 版本1

6. 环境变量：

```
HUAWEI_CLOUD_AK=HPUACBZNVJEWFWDF8ZEW
HUAWEI_CLOUD_SK=PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu
HUAWEI_CLOUD_REGION=cn-north-4
OBS_BUCKET_NAME=video-vault-storage
OBS_ENDPOINT=obs.cn-north-4.myhuaweicloud.com
LLM_API_KEY=sk-B2WnTcrxS5MzRvNngtoy9NtSDq4Yt7toOVF2E02WA8ubf8pG
LLM_API_BASE=https://api.chatanywhere.tech/v1
LLM_MODEL=gpt-4o-mini
```

7. 点击 **创建函数**

#### 7.4.3 配置API网关触发器（重要！）

AI Agent需要HTTP访问，必须配置APIG触发器：

1. 进入 `video-vault-ai-agent` 函数详情页
2. 点击 **触发器** 标签
3. 点击 **创建触发器**
4. 配置：

```
触发器类型: APIG (API网关)
API名称: video-vault-ai-api
API分组: 【选择已有或新建】default
安全认证: NONE (无认证)  【生产环境建议使用APP认证】
协议: HTTPS
请求方法: POST
路径: /ai-agent
后端超时: 30000 毫秒
```

5. 点击 **确定**

#### 7.4.4 记录API URL

创建成功后，会显示API调用地址：

```
https://xxxxxxxxxx.apig.cn-north-4.huaweicloudapis.com/ai-agent
```

**重要**: 保存这个URL，需要配置到前端！

---

### 7.5 配置OBS触发器（关键！）

为 `video-vault-slicer` 函数配置OBS触发器，实现自动处理。

1. 打开 `video-vault-slicer` 函数详情页
2. 点击 **触发器** 标签
3. 点击 **创建触发器**
4. 配置：

```
触发器类型: 对象存储服务 OBS
桶名称: video-vault-storage
触发事件:
  ✅ PUT - 上传对象
  ✅ POST - 上传对象
前缀: uploads/
后缀: .mp4
```

**解释**:
- 只有上传到 `uploads/` 目录的 `.mp4` 文件才会触发
- 避免循环触发（其他目录的文件不触发）

5. 点击 **确定**

---

## 8. 配置前端

### 8.1 配置前端环境变量

编辑 `frontend/.env` 文件（已创建好）：

```bash
# Video Vault 前端环境变量配置

# 华为云访问密钥
VITE_HUAWEI_CLOUD_AK=HPUACBZNVJEWFWDF8ZEW
VITE_HUAWEI_CLOUD_SK=PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu

# OBS对象存储配置
VITE_OBS_BUCKET_NAME=video-vault-storage
VITE_OBS_ENDPOINT=https://obs.cn-north-4.myhuaweicloud.com

# 华为云Region配置
VITE_HUAWEI_CLOUD_REGION=cn-north-4

# AI Agent API Gateway URL（填入刚才记录的API URL）
VITE_AI_AGENT_API_URL=https://xxxxxxxxxx.apig.cn-north-4.huaweicloudapis.com/ai-agent

# 应用配置
VITE_APP_TITLE=Video Vault - 视频DLP系统
VITE_APP_MODE=serverless
```

**重要**: 将 `VITE_AI_AGENT_API_URL` 修改为你的实际API Gateway URL！

### 8.2 安装前端依赖

```bash
cd frontend
npm install
```

### 8.3 启动前端开发服务器

```bash
npm run dev
```

访问: http://localhost:5173

### 8.4 构建生产版本（可选）

```bash
npm run build
```

生成的文件在 `frontend/dist/` 目录，可以部署到：
- 华为云OBS（静态网站托管）
- 华为云CDN
- Nginx
- 其他静态托管服务

---

## 9. 测试验证

### 9.1 完整流程测试

#### 步骤1: 上传测试视频

1. 打开前端页面 http://localhost:5173
2. 点击 **视频上传**
3. 选择一个测试视频（建议<100MB，时长<5分钟）
4. 点击 **开始上传**

**预期结果**:
```
正在上传... 30%
正在上传... 60%
上传完成，云函数处理中...
处理中... (等待5秒后自动查询)
处理中... (等待5秒后自动查询)
...
✅ 处理完成！检测到 3 个敏感信息
```

#### 步骤2: 查看函数执行日志

**查看video-vault-slicer日志**:
1. FunctionGraph控制台 → `video-vault-slicer` → **监控** → **日志**
2. 应该看到：
   ```
   [INFO] 收到OBS上传事件
   [INFO] 处理视频: uploads/test_video.mp4
   [INFO] 视频已下载: /tmp/test_video.mp4
   [INFO] 切片完成: 3 个切片
   [INFO] 切片已上传到OBS: 3 个
   [INFO] 已触发 3 个DLP扫描函数
   ```

**查看video-vault-dlp日志**:
1. FunctionGraph控制台 → `video-vault-dlp` → **监控** → **日志**
2. 应该看到3条记录（每个切片一条）：
   ```
   [INFO] 收到DLP扫描任务
   [INFO] 切片已下载: /tmp/test_video_slice_0.mp4
   [INFO] 提取了 60 个关键帧
   [INFO] 发现 2 帧包含敏感信息
   [INFO] 切片脱敏完成
   [INFO] 审计日志已保存到OBS: logs/test_video_audit.json
   ```

**查看video-vault-merger日志**:
1. FunctionGraph控制台 → `video-vault-merger` → **监控** → **日志**
2. 应该看到：
   ```
   [INFO] 收到视频合并任务
   [INFO] 已下载 3 个切片
   [INFO] 视频合并完成: /tmp/test_video_sanitized.mp4
   [INFO] 合并视频已上传: outputs/test_video_sanitized.mp4
   [INFO] 视频 test_video 处理完成
   ```

#### 步骤3: 查看OBS输出

1. 登录OBS控制台
2. 进入 `video-vault-storage` 桶
3. 检查目录：

```
video-vault-storage/
├── uploads/
│   └── test_video.mp4              # 原始上传
├── slices/test_video/
│   ├── slice_0000.mp4              # 切片
│   ├── slice_0001.mp4
│   └── slice_0002.mp4
├── processed/test_video/
│   ├── slice_0000.mp4              # 处理后的切片
│   ├── slice_0001.mp4
│   └── slice_0002.mp4
├── outputs/
│   └── test_video_sanitized.mp4    # ✅ 最终输出
└── logs/
    └── test_video_audit.json       # ✅ 审计日志
```

#### 步骤4: 下载并查看结果

1. 在前端 **视频管理** 页面
2. 找到刚才上传的视频
3. 点击 **下载** 按钮
4. 播放下载的视频，验证敏感信息已被模糊处理

#### 步骤5: 查看审计日志

1. 前端 **审计日志** 页面
2. 应该能看到检测到的敏感信息记录
3. 包含：时间戳、类型、置信度、位置等

#### 步骤6: 测试AI对话

1. 前端 **AI助手** 页面
2. 输入问题：
   ```
   查询最近的审计日志
   ```
3. AI应该返回类似：
   ```
   根据审计日志，最近处理的视频 test_video 中检测到 3 处敏感信息：
   - 身份证号: 2次
   - 手机号: 1次

   建议重点关注该视频的安全风险。
   ```

### 9.2 并发测试（可选）

测试系统并发处理能力：

```bash
# 批量上传5个视频
for i in {1..5}; do
  echo "上传视频 $i"
  # 使用前端或OBS Browser上传
done
```

**监控函数实例数**:
- FunctionGraph控制台 → 各函数 → **监控** → **实例数**
- 应该看到：
  - `video-vault-slicer`: 5个实例
  - `video-vault-dlp`: 15-30个实例（并行处理切片）
  - `video-vault-merger`: 5个实例

---

## 10. 监控和优化

### 10.1 配置监控告警

1. FunctionGraph控制台 → **告警规则** → **创建告警规则**
2. 配置告警指标：

```
告警名称: video-vault-error-alert
监控对象: 选择所有4个函数
监控指标:
  - 错误次数 > 5 (5分钟)
  - 执行超时 > 3 (5分钟)
  - 平均执行时间 > 60000ms
通知方式: 短信 + 邮件
```

### 10.2 查看用量统计

1. FunctionGraph控制台 → **用量统计**
2. 查看：
   - 调用次数
   - GB-秒（内存×时间）
   - 预估费用

### 10.3 成本优化建议

**OBS生命周期规则**:

1. OBS控制台 → `video-vault-storage` → **生命周期规则**
2. 创建规则：

```
规则1: 清理临时切片
前缀: slices/
保留时间: 1天
操作: 删除对象

规则2: 清理处理后切片
前缀: processed/
保留时间: 3天
操作: 删除对象

规则3: 转换冷存储
前缀: outputs/
保留时间: 30天
操作: 转换到低频存储
```

**函数优化**:

- 调整内存规格（根据实际使用率）
- 减少超时时间（根据实际执行时间）
- 使用预留实例（高频函数）

---

## 11. 常见问题

### Q1: 函数执行超时

**症状**: 日志显示 `Task timed out after 900.00 seconds`

**原因**:
- 视频太大
- 切片太多
- 网络慢

**解决**:
1. 检查视频大小，建议单个视频<500MB
2. 调整切片时长 `SLICE_DURATION=30` (减小到30秒)
3. 增加函数内存（内存越大，CPU越强）

---

### Q2: 内存不足 (OOM)

**症状**: 日志显示 `MemoryError` 或进程被杀

**原因**:
- 函数内存配置不足
- 临时文件未清理

**解决**:
1. 增加函数内存到 3072MB 或 4096MB
2. 检查代码是否正确清理临时文件

---

### Q3: OBS访问权限错误

**症状**: 日志显示 `Access Denied` 或 `403 Forbidden`

**原因**:
- AK/SK不正确
- CORS未配置
- 桶策略限制

**解决**:
1. 验证AK/SK是否正确
2. 检查OBS CORS配置（参见5.3节）
3. 检查桶策略是否允许访问

---

### Q4: 函数之间调用失败

**症状**: 日志显示 `Failed to invoke function`

**原因**:
- 函数URN不正确
- 函数不在同一区域
- 权限不足

**解决**:
1. 检查环境变量中的URN格式：
   ```
   urn:fss:cn-north-4:xxxxx:function:default:函数名:latest
   ```
2. 确认所有函数都在 `cn-north-4` 区域
3. 检查函数委托权限

---

### Q5: AI Agent返回503错误

**症状**: 前端调用AI Agent返回 `503 Service Unavailable`

**原因**:
- LLM_API_KEY未配置或错误
- API余额不足
- 网络问题

**解决**:
1. 检查环境变量 `LLM_API_KEY` 是否正确
2. 访问 https://api.chatanywhere.tech 查看余额
3. 测试API是否可用：
   ```bash
   curl https://api.chatanywhere.tech/v1/chat/completions \
     -H "Authorization: Bearer $LLM_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hi"}]}'
   ```

---

### Q6: 前端无法访问OBS

**症状**: 前端显示 `CORS policy` 错误

**原因**:
- OBS CORS未配置
- 前端环境变量不正确

**解决**:
1. 检查OBS CORS配置（参见5.3节）
2. 验证 `frontend/.env` 中的配置
3. 清除浏览器缓存重试

---

### Q7: 视频处理卡住不动

**症状**: 前端一直显示"处理中"

**原因**:
- 某个函数执行失败
- 合并函数未触发
- 网络问题

**解决**:
1. 查看3个函数的日志，找出失败原因
2. 手动触发合并函数测试：
   - 进入 `video-vault-merger` 函数
   - 点击 **测试**
   - 输入测试事件：
     ```json
     {
       "video_id": "test_video",
       "total_slices": 3,
       "bucket_name": "video-vault-storage"
     }
     ```
   - 点击 **执行**

---

### Q8: 依赖层加载失败

**症状**: 日志显示 `ModuleNotFoundError: No module named 'xxx'`

**原因**:
- 依赖层未挂载
- 依赖层打包错误
- Python版本不匹配

**解决**:
1. 检查函数是否挂载了依赖层
2. 重新打包依赖层（使用Python 3.9）:
   ```bash
   rm -rf layers/ deploy/
   python3.9 build_layers.py
   ```
3. 重新上传依赖层

---

## 📊 部署完成检查清单

部署完成后，请确认以下所有项：

- [ ] OBS存储桶 `video-vault-storage` 已创建
- [ ] OBS CORS已配置
- [ ] OBS目录结构已创建（uploads/, outputs/, logs/等）
- [ ] 依赖层 `video-vault-python-deps` 已上传
- [ ] 4个云函数已创建并运行正常
- [ ] 所有函数已挂载依赖层
- [ ] 所有环境变量已正确配置
- [ ] 函数URN已相互引用
- [ ] OBS触发器已配置到 `video-vault-slicer`
- [ ] API网关已配置到 `video-vault-ai-agent`
- [ ] 前端环境变量已配置（frontend/.env）
- [ ] 测试视频上传处理成功
- [ ] 前端能正常查看视频列表
- [ ] 前端能正常查看审计日志
- [ ] AI对话功能正常工作
- [ ] 监控告警已配置

---

## 🎉 部署成功！

恭喜你完成了 Video Vault 的完全Serverless部署！

### 系统架构总结

- ✅ **完全无服务器** - 无需管理服务器
- ✅ **按需付费** - 只为实际使用付费
- ✅ **自动伸缩** - 自动应对并发请求
- ✅ **高可用** - 华为云保障99.95%可用性
- ✅ **数据安全** - OBS加密存储，审计日志完整

### 后续操作建议

1. **生产环境优化**:
   - 配置自定义域名
   - 启用HTTPS
   - 配置API认证（APP签名）
   - 配置备份策略

2. **成本优化**:
   - 配置OBS生命周期规则
   - 根据实际用量调整函数规格
   - 使用预留实例降低成本

3. **监控运维**:
   - 配置告警规则
   - 定期查看日志
   - 优化函数性能

### 技术支持

- 华为云文档: https://support.huaweicloud.com/functiongraph/
- GitHub Issues: https://github.com/your-repo/video-vault/issues
- 邮件: support@your-domain.com

---

**享受完全Serverless的视频DLP系统！** 🚀

---

*文档版本: v2.0*
*最后更新: 2024年*
*适用架构: 华为云FunctionGraph + OBS*
