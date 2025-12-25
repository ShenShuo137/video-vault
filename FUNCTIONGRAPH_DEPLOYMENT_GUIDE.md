# 华为云FunctionGraph部署完整指南

> 详细的云函数创建和配置步骤（4个函数 + 依赖层）

---

## 📋 目录

1. [前置准备](#1-前置准备)
2. [打包部署文件](#2-打包部署文件)
3. [上传依赖层](#3-上传依赖层)
4. [创建云函数](#4-创建云函数)
   - [函数1: video-vault-slicer](#函数1-video-vault-slicer-视频切片)
   - [函数2: video-vault-dlp](#函数2-video-vault-dlp-dlp扫描)
   - [函数3: video-vault-merger](#函数3-video-vault-merger-视频合并)
   - [函数4: video-vault-ai-agent](#函数4-video-vault-ai-agent-ai助手)
5. [配置触发器](#5-配置触发器)
6. [测试部署](#6-测试部署)
7. [常见问题](#7-常见问题)

---

## 1. 前置准备

### ✅ 确认已完成

- [x] 华为云账号已开通
- [x] 已开通服务：FunctionGraph、OBS、OCR、MPC、RDS MySQL
- [x] OBS存储桶已创建（如 `video-vault-storage`）
- [x] OBS目录结构已创建：
  ```
  video-vault-storage/
  ├── uploads/      # 上传目录（触发点）
  ├── slices/       # 切片临时目录
  ├── processed/    # 处理后切片目录
  ├── outputs/      # 最终输出目录
  └── logs/         # 审计日志目录
  ```
- [x] MySQL数据库已创建（可选，用于数据库审计日志）
- [x] `.env` 文件已配置

### 📝 记录以下信息

在部署过程中你需要用到这些信息，请提前准备：

```bash
# 华为云账号信息
HUAWEI_CLOUD_AK=your_access_key
HUAWEI_CLOUD_SK=your_secret_key
HUAWEI_CLOUD_REGION=cn-north-4  # 你的区域
PROJECT_ID=your_project_id      # 区域对应的项目ID

# OBS信息
OBS_BUCKET_NAME=video-vault-storage
OBS_ENDPOINT=https://obs.cn-north-4.myhuaweicloud.com

# 数据库信息（可选）
DB_HOST=your_rds_host
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=video_vault

# AI Agent信息（可选）
LLM_API_KEY=sk-xxx
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-4
```

---

## 2. 打包部署文件

### 步骤1: 运行打包脚本

在项目根目录执行：

```bash
python build_layers.py
```

### 步骤2: 确认生成的文件

打包成功后，会生成以下文件：

```
video-vault/
├── layers/
│   └── python-deps.zip         # 依赖层（约50-80MB）
└── deploy/
    ├── video_slicer.zip        # 函数1代码
    ├── dlp_scanner.zip         # 函数2代码
    ├── video_merger.zip        # 函数3代码
    └── ai_agent.zip            # 函数4代码
```

**注意事项**：
- `python-deps.zip` 大小不能超过100MB（华为云限制）
- 如果超过，需要删除不必要的依赖或使用特定版本
- 打包过程可能需要5-10分钟（opencv较大）

---

## 3. 上传依赖层

依赖层是共享的Python依赖库，所有函数都会使用。

### 步骤1: 登录FunctionGraph控制台

1. 登录华为云控制台
2. 搜索并打开 **FunctionGraph**
3. 选择你的区域（如 `华北-北京四 cn-north-4`）

### 步骤2: 创建依赖层

1. 点击左侧菜单 **依赖包** → **依赖层**
2. 点击右上角 **创建依赖层**
3. 填写配置：

   ```
   名称: video-vault-python-deps
   运行时: Python 3.9
   上传方式: 本地ZIP
   文件: 选择 layers/python-deps.zip
   描述: Video Vault Python依赖层（包含所有SDK和工具库）
   ```

4. 点击 **创建**，等待上传完成（可能需要1-2分钟）

### 步骤3: 记录依赖层信息

创建成功后，记录依赖层的ARN（后续创建函数时需要）：

```
arn:cn-north-4:xxxx:layerVersion:video-vault-python-deps:1
```

---

## 4. 创建云函数

我们需要创建4个云函数，以下是详细步骤。

---

### 函数1: video-vault-slicer（视频切片）

#### 作用
接收OBS上传事件，将视频切片为多个小段，并触发DLP扫描。

#### 创建步骤

1. **进入创建页面**
   - FunctionGraph控制台 → 点击 **创建函数**
   - 选择 **从头开始创建**

2. **基本信息**
   ```
   函数名称: video-vault-slicer
   企业项目: default
   委托名称: （暂不选择）
   运行时: Python 3.9
   函数类型: 事件函数
   ```

3. **代码配置**
   ```
   代码上传方式: 本地ZIP
   选择文件: deploy/video_slicer.zip
   函数执行入口: video_slicer_handler.handler
   ```

   **解释**：`handler` 是 `video_slicer_handler.py` 中的 `handler` 函数

4. **高级配置**
   ```
   内存规格: 2048 MB  （视频处理需要较大内存）
   超时时间: 900 秒   （15分钟，处理大视频）
   并发配置: 保留实例数 0，最大实例数 100
   ```

5. **依赖层配置**
   - 点击 **添加依赖层**
   - 选择刚才创建的 `video-vault-python-deps`

6. **环境变量**（点击 **环境变量** 标签）

   添加以下环境变量：
   ```
   HUAWEI_CLOUD_AK=your_access_key
   HUAWEI_CLOUD_SK=your_secret_key
   HUAWEI_CLOUD_REGION=cn-north-4
   OBS_BUCKET_NAME=video-vault-storage
   OBS_ENDPOINT=https://obs.cn-north-4.myhuaweicloud.com

   DLP_SCANNER_FUNCTION_URN=（暂时留空，后面填写）

   DB_HOST=your_rds_host
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=video_vault
   ```

   **注意**：
   - `DLP_SCANNER_FUNCTION_URN` 需要在创建函数2后回来填写
   - 数据库配置是可选的（如果不需要数据库审计日志，可以不填）

7. **点击 创建** 完成

#### 记录函数URN

创建成功后，进入函数详情页，复制函数的URN：

```
urn:fss:cn-north-4:xxxx:function:default:video-vault-slicer:latest
```

**保存这个URN，后面配置触发器时需要用到！**

---

### 函数2: video-vault-dlp（DLP扫描）

#### 作用
接收视频切片，进行OCR扫描和敏感信息脱敏处理。

#### 创建步骤

1. **进入创建页面**
   - FunctionGraph控制台 → **创建函数** → **从头开始创建**

2. **基本信息**
   ```
   函数名称: video-vault-dlp
   运行时: Python 3.9
   函数类型: 事件函数
   ```

3. **代码配置**
   ```
   代码上传方式: 本地ZIP
   选择文件: deploy/dlp_scanner.zip
   函数执行入口: dlp_scanner_handler.handler
   ```

4. **高级配置**
   ```
   内存规格: 2048 MB  （OCR需要较大内存）
   超时时间: 900 秒
   并发配置: 最大实例数 200  （支持并行处理多个切片）
   ```

5. **依赖层**
   - 添加依赖层 `video-vault-python-deps`

6. **环境变量**
   ```
   HUAWEI_CLOUD_AK=your_access_key
   HUAWEI_CLOUD_SK=your_secret_key
   HUAWEI_CLOUD_REGION=cn-north-4
   OBS_BUCKET_NAME=video-vault-storage
   OBS_ENDPOINT=https://obs.cn-north-4.myhuaweicloud.com

   VIDEO_MERGER_FUNCTION_URN=（暂时留空，后面填写）

   OCR_CONFIDENCE_THRESHOLD=0.7
   BLUR_INTENSITY=50

   DB_HOST=your_rds_host
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=video_vault
   ```

7. **点击 创建**

#### 记录函数URN

复制函数URN：
```
urn:fss:cn-north-4:xxxx:function:default:video-vault-dlp:latest
```

#### ⚠️ 重要：回填函数1的环境变量

现在我们有了DLP函数的URN，需要回到函数1填写：

1. 打开 **video-vault-slicer** 函数
2. 点击 **配置** → **环境变量**
3. 编辑 `DLP_SCANNER_FUNCTION_URN`，填入刚才复制的URN
4. 保存

---

### 函数3: video-vault-merger（视频合并）

#### 作用
接收所有处理完的切片，合并为完整视频并输出到OBS。

#### 创建步骤

1. **进入创建页面**
   - FunctionGraph控制台 → **创建函数** → **从头开始创建**

2. **基本信息**
   ```
   函数名称: video-vault-merger
   运行时: Python 3.9
   函数类型: 事件函数
   ```

3. **代码配置**
   ```
   代码上传方式: 本地ZIP
   选择文件: deploy/video_merger.zip
   函数执行入口: video_merger_handler.handler
   ```

4. **高级配置**
   ```
   内存规格: 2048 MB  （视频合并需要较大内存）
   超时时间: 900 秒
   并发配置: 最大实例数 10  （合并操作不需要太高并发）
   ```

5. **依赖层**
   - 添加依赖层 `video-vault-python-deps`

6. **环境变量**
   ```
   HUAWEI_CLOUD_AK=your_access_key
   HUAWEI_CLOUD_SK=your_secret_key
   HUAWEI_CLOUD_REGION=cn-north-4
   OBS_BUCKET_NAME=video-vault-storage
   OBS_ENDPOINT=https://obs.cn-north-4.myhuaweicloud.com

   DB_HOST=your_rds_host
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=video_vault
   ```

7. **点击 创建**

#### 记录函数URN

复制函数URN：
```
urn:fss:cn-north-4:xxxx:function:default:video-vault-merger:latest
```

#### ⚠️ 重要：回填函数2的环境变量

1. 打开 **video-vault-dlp** 函数
2. 点击 **配置** → **环境变量**
3. 编辑 `VIDEO_MERGER_FUNCTION_URN`，填入刚才复制的URN
4. 保存

---

### 函数4: video-vault-ai-agent（AI助手）

#### 作用
通过HTTP API提供AI对话功能，查询视频审计日志和统计信息。

#### 创建步骤

1. **进入创建页面**
   - FunctionGraph控制台 → **创建函数** → **从头开始创建**

2. **基本信息**
   ```
   函数名称: video-vault-ai-agent
   运行时: Python 3.9
   函数类型: 事件函数  （⚠️ 选择事件函数，不是HTTP函数）
   ```

3. **代码配置**
   ```
   代码上传方式: 本地ZIP
   选择文件: deploy/ai_agent.zip
   函数执行入口: ai_agent_handler.handler
   ```

4. **高级配置**
   ```
   内存规格: 1024 MB  （AI对话不需要太大内存）
   超时时间: 300 秒
   并发配置: 最大实例数 50
   ```

5. **依赖层**
   - 添加依赖层 `video-vault-python-deps`

6. **环境变量**
   ```
   HUAWEI_CLOUD_AK=your_access_key
   HUAWEI_CLOUD_SK=your_secret_key
   HUAWEI_CLOUD_REGION=cn-north-4
   OBS_BUCKET_NAME=video-vault-storage
   OBS_ENDPOINT=https://obs.cn-north-4.myhuaweicloud.com

   LLM_API_KEY=sk-xxx
   LLM_API_BASE=https://api.openai.com/v1
   LLM_MODEL=gpt-4

   DB_HOST=your_rds_host
   DB_PORT=3306
   DB_USER=root
   DB_PASSWORD=your_password
   DB_NAME=video_vault
   ```

   **重要**：
   - `LLM_API_KEY` 是OpenAI API密钥（必须配置，否则AI功能无法使用）
   - 如果使用其他LLM服务（如Azure OpenAI），修改 `LLM_API_BASE`

7. **点击 创建**

#### 配置API触发器（重要！）

AI Agent需要HTTP访问，必须配置API Gateway触发器：

1. 进入 **video-vault-ai-agent** 函数详情页
2. 点击 **触发器** 标签
3. 点击 **创建触发器**
4. 配置如下：

   ```
   触发器类型: APIG（API网关）
   API名称: video-vault-ai-agent-api
   分组: 选择已有分组或创建新分组
   安全认证:
     - 开发测试: 选择 "NONE"（无认证）
     - 生产环境: 选择 "APP"（需要创建API访问凭证）
   协议: HTTPS
   请求方法: POST
   路径: /ai-agent
   后端超时: 30000 ms
   ```

5. 点击 **确定** 创建

#### 记录API Gateway URL

创建成功后，会显示API的调用地址：

```
https://xxxx.apig.cn-north-4.huaweicloudapis.com/ai-agent
```

**保存这个URL，需要配置到前端环境变量中！**

#### 配置前端环境变量

编辑 `frontend/.env`，添加：

```bash
VITE_AI_AGENT_API_URL=https://xxxx.apig.cn-north-4.huaweicloudapis.com/ai-agent
```

---

## 5. 配置触发器

### 5.1 为video-vault-slicer配置OBS触发器

这是最关键的触发器，当用户上传视频到OBS时自动启动处理流程。

#### 步骤

1. 打开 **video-vault-slicer** 函数详情页
2. 点击 **触发器** 标签
3. 点击 **创建触发器**
4. 配置：

   ```
   触发器类型: 对象存储服务OBS
   桶名称: video-vault-storage
   触发事件:
     ✅ PUT - 创建对象
     ✅ POST - 创建对象
   前缀: uploads/
   后缀: .mp4
   ```

   **解释**：
   - 只有上传到 `uploads/` 目录的 `.mp4` 文件才会触发
   - 避免触发器循环触发（处理后的文件在 `outputs/` 不会触发）

5. 点击 **确定**

#### 测试触发器

上传一个测试视频到OBS：

```bash
# 使用OBS Browser或obsutil上传
obsutil cp test.mp4 obs://video-vault-storage/uploads/test.mp4
```

查看函数日志：
- FunctionGraph控制台 → **video-vault-slicer** → **监控** → **日志**
- 应该看到触发记录和执行日志

---

### 5.2 其他函数的触发方式

- **video-vault-dlp**: 由 `video-vault-slicer` 通过SDK调用（无需配置触发器）
- **video-vault-merger**: 由 `video-vault-dlp` 通过SDK调用（无需配置触发器）
- **video-vault-ai-agent**: 已配置API Gateway触发器（第4步完成）

---

## 6. 测试部署

### 6.1 完整流程测试

1. **上传测试视频**

   通过OBS控制台或obsutil上传视频：
   ```bash
   obsutil cp sample_video.mp4 obs://video-vault-storage/uploads/sample_video.mp4
   ```

2. **检查函数执行**

   依次查看3个函数的日志：

   - **video-vault-slicer**
     ```
     FunctionGraph → video-vault-slicer → 监控 → 日志
     ```
     应该看到：
     ```
     [INFO] 收到OBS上传事件
     [INFO] 开始切片: sample_video.mp4
     [INFO] 切片完成，共3个切片
     [INFO] 已触发3个DLP扫描任务
     ```

   - **video-vault-dlp**
     ```
     FunctionGraph → video-vault-dlp → 监控 → 日志
     ```
     应该看到多条记录（每个切片一条）：
     ```
     [INFO] 收到DLP扫描任务: slice_0
     [INFO] 提取了30个关键帧
     [INFO] 发现5帧包含敏感信息
     [INFO] 切片脱敏完成
     [INFO] 审计日志已保存到OBS
     ```

   - **video-vault-merger**
     ```
     FunctionGraph → video-vault-merger → 监控 → 日志
     ```
     应该看到：
     ```
     [INFO] 收到视频合并任务
     [INFO] 下载了3个切片
     [INFO] 合并完成，输出到outputs/
     ```

3. **检查OBS输出**

   登录OBS控制台，查看：
   ```
   video-vault-storage/
   ├── uploads/sample_video.mp4          # 原始上传
   ├── outputs/sample_video_sanitized.mp4  # 处理后的视频 ✅
   └── logs/sample_video_audit.json       # 审计日志 ✅
   ```

4. **测试AI Agent**

   使用curl测试AI Agent API：
   ```bash
   curl -X POST "https://xxxx.apig.cn-north-4.huaweicloudapis.com/ai-agent" \
     -H "Content-Type: application/json" \
     -d '{
       "action": "chat",
       "message": "查询最近的审计日志"
     }'
   ```

   应该返回：
   ```json
   {
     "response": "根据审计日志，最近处理的视频...",
     "timestamp": "..."
   }
   ```

5. **测试前端**

   启动前端开发服务器：
   ```bash
   cd frontend
   npm run dev
   ```

   访问 `http://localhost:5173`：
   - ✅ 上传视频
   - ✅ 查看处理进度
   - ✅ 下载处理后视频
   - ✅ 查看审计日志
   - ✅ AI对话功能

---

### 6.2 性能测试

测试并发处理能力：

1. **批量上传多个视频**
   ```bash
   for i in {1..10}; do
     obsutil cp video_$i.mp4 obs://video-vault-storage/uploads/video_$i.mp4
   done
   ```

2. **监控函数并发**

   FunctionGraph控制台 → 各函数 → **监控** → **实例**

   应该看到：
   - `video-vault-slicer`: 10个实例（每个视频一个）
   - `video-vault-dlp`: 30+个实例（并行处理所有切片）
   - `video-vault-merger`: 10个实例

3. **检查成本**

   FunctionGraph控制台 → **用量统计**

   查看：
   - 调用次数
   - GB-秒（内存*时间）
   - 预估费用

---

## 7. 常见问题

### Q1: 函数执行超时

**症状**: 函数日志显示 `Task timed out after 300.00 seconds`

**解决方案**:
- 增加函数超时时间：函数配置 → 高级配置 → 超时时间改为 900秒
- 对于大视频（>500MB），考虑增加到最大值 900秒

---

### Q2: 内存不足 (OOM)

**症状**: 日志显示 `MemoryError` 或 `Killed`

**解决方案**:
- 增加函数内存：函数配置 → 高级配置 → 内存规格改为 3072MB 或 4096MB
- 检查是否有内存泄漏（临时文件未删除）

---

### Q3: 依赖层加载失败

**症状**: 日志显示 `ModuleNotFoundError: No module named 'xxx'`

**解决方案**:
1. 检查依赖层是否正确挂载：函数配置 → 依赖层
2. 重新打包依赖层：
   ```bash
   rm -rf layers/
   python build_layers.py
   ```
3. 检查依赖层大小是否超过100MB

---

### Q4: OBS触发器不工作

**症状**: 上传视频后函数没有被触发

**解决方案**:
1. 检查触发器配置：
   - 前缀必须是 `uploads/`
   - 后缀必须是 `.mp4`
2. 确认上传路径正确：
   ```bash
   # 正确 ✅
   obs://video-vault-storage/uploads/test.mp4

   # 错误 ❌
   obs://video-vault-storage/test.mp4
   ```
3. 查看OBS事件通知日志：
   OBS控制台 → 事件通知 → 查看记录

---

### Q5: 函数之间调用失败

**症状**: 日志显示 `Failed to invoke function`

**解决方案**:
1. 检查环境变量中的URN是否正确：
   ```bash
   # 格式必须是：
   urn:fss:cn-north-4:xxxx:function:default:函数名:latest
   ```
2. 检查函数权限（委托配置）
3. 确认所有函数都在同一区域

---

### Q6: AI Agent返回错误

**症状**: API返回 `503 Service Unavailable` 或 `AI Agent未配置`

**解决方案**:
1. 检查环境变量：
   ```bash
   LLM_API_KEY=sk-xxx  # 必须配置
   LLM_API_BASE=https://api.openai.com/v1
   LLM_MODEL=gpt-4
   ```
2. 测试API密钥是否有效：
   ```bash
   curl https://api.openai.com/v1/chat/completions \
     -H "Authorization: Bearer $LLM_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"gpt-4","messages":[{"role":"user","content":"test"}]}'
   ```
3. 检查函数日志的详细错误信息

---

### Q7: API Gateway CORS错误

**症状**: 前端调用AI Agent API时显示 `CORS policy` 错误

**解决方案**:
1. 确认函数返回了CORS头：
   ```python
   "headers": {
       "Content-Type": "application/json",
       "Access-Control-Allow-Origin": "*"  # ← 必须有
   }
   ```
2. API Gateway配置CORS：
   - APIG控制台 → API → 编辑
   - 启用跨域访问支持
   - 允许的Origin: `*` 或具体域名

---

### Q8: 审计日志查询不到

**症状**: 前端显示"无审计日志"

**解决方案**:
1. 检查OBS `logs/` 目录是否有JSON文件
2. 确认DLP扫描函数执行成功（查看日志）
3. 检查日志文件格式：
   ```bash
   # 下载日志文件检查
   obsutil cp obs://video-vault-storage/logs/xxx_audit.json ./
   cat xxx_audit.json
   ```
4. 确认前端OBS配置正确（AK/SK）

---

### Q9: 视频处理卡住不动

**症状**: 视频一直显示"处理中"，从不完成

**解决方案**:
1. 查看3个函数的日志，找出卡在哪一步
2. 常见原因：
   - 最后一个切片处理失败 → 合并函数没触发
   - 合并函数内存不足 → 增加内存
   - 临时文件占满 `/tmp` → 优化代码清理临时文件
3. 手动触发合并函数测试：
   ```json
   {
     "video_id": "xxx",
     "total_slices": 3,
     "bucket_name": "video-vault-storage"
   }
   ```

---

## 📊 部署完成检查清单

部署完成后，请确认以下所有项：

- [ ] 4个云函数已创建并正常运行
- [ ] 依赖层已上传并挂载到所有函数
- [ ] 所有环境变量已正确配置
- [ ] OBS触发器已配置到 `video-vault-slicer`
- [ ] API Gateway已配置到 `video-vault-ai-agent`
- [ ] 函数之间的URN引用已正确填写
- [ ] 上传测试视频能成功处理
- [ ] 前端能正常上传、查询、下载
- [ ] AI对话功能正常工作
- [ ] 审计日志能正常查询

---

## 🎉 部署成功！

恭喜，Video Vault已完全部署到华为云Serverless架构！

**后续操作**：
1. 配置域名（可选）：APIG绑定自定义域名
2. 启用HTTPS（推荐）：上传SSL证书
3. 配置监控告警（推荐）：设置函数失败告警
4. 成本优化（可选）：根据用量调整函数规格

**享受完全Serverless的视频DLP系统！** 🚀
