# 云函数环境变量配置清单

## ⚠️ 重要提示
每个云函数都需要在华为云控制台单独配置环境变量！

## 配置位置
在每个函数的 **配置** 标签 → **环境变量** 部分

---

## 1️⃣ video-vault-slicer 环境变量

| 变量名 | 值（示例） | 说明 |
|-------|----------|------|
| `HUAWEI_CLOUD_AK` | `HPUACBZNVJEWFWDF8ZEW` | 华为云访问密钥 |
| `HUAWEI_CLOUD_SK` | `PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu` | 华为云私密密钥 |
| `HUAWEI_CLOUD_REGION` | `cn-north-4` | 华为云区域 |
| `OBS_BUCKET_NAME` | `video-vault-storage` | OBS桶名称 |
| `SLICE_DURATION` | `30` | 切片时长（秒） |
| `DLP_SCANNER_FUNCTION_URN` | `urn:fss:cn-north-4:96c5e3fa586c486e977707f516a95e4d:function:default:video-vault-dlp-scanner:latest` | DLP扫描函数URN |

### 如何获取 DLP_SCANNER_FUNCTION_URN？
1. 进入 `video-vault-dlp-scanner` 函数页面
2. 在函数基本信息中找到 **函数URN**
3. 复制整个 URN（格式：`urn:fss:区域:项目ID:function:default:函数名:版本`）

---

## 2️⃣ video-vault-dlp-scanner 环境变量

| 变量名 | 值（示例） | 说明 |
|-------|----------|------|
| `HUAWEI_CLOUD_AK` | `HPUACBZNVJEWFWDF8ZEW` | 华为云访问密钥 |
| `HUAWEI_CLOUD_SK` | `PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu` | 华为云私密密钥 |
| `HUAWEI_CLOUD_REGION` | `cn-north-4` | 华为云区域 |
| `OBS_BUCKET_NAME` | `video-vault-storage` | OBS桶名称 |
| `OCR_PROJECT_ID` | `96c5e3fa586c486e977707f516a95e4d` | OCR服务项目ID |
| `OCR_CONFIDENCE_THRESHOLD` | `0.6` | OCR置信度阈值 |
| `BLUR_INTENSITY` | `30` | 模糊强度 |
| `VIDEO_MERGER_FUNCTION_URN` | `urn:fss:cn-north-4:96c5e3fa586c486e977707f516a95e4d:function:default:video-vault-merger:latest` | 合并函数URN |

---

## 3️⃣ video-vault-merger 环境变量

| 变量名 | 值（示例） | 说明 |
|-------|----------|------|
| `HUAWEI_CLOUD_AK` | `HPUACBZNVJEWFWDF8ZEW` | 华为云访问密钥 |
| `HUAWEI_CLOUD_SK` | `PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu` | 华为云私密密钥 |
| `HUAWEI_CLOUD_REGION` | `cn-north-4` | 华为云区域 |
| `OBS_BUCKET_NAME` | `video-vault-storage` | OBS桶名称 |

---

## 4️⃣ video-vault-ai-agent 环境变量

| 变量名 | 值（示例） | 说明 |
|-------|----------|------|
| `HUAWEI_CLOUD_AK` | `HPUACBZNVJEWFWDF8ZEW` | 华为云访问密钥 |
| `HUAWEI_CLOUD_SK` | `PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu` | 华为云私密密钥 |
| `HUAWEI_CLOUD_REGION` | `cn-north-4` | 华为云区域 |
| `OBS_BUCKET_NAME` | `video-vault-storage` | OBS桶名称 |
| `LLM_API_KEY` | `sk-B2WnTcrxS5MzRvNngtoy9NtSDq4Yt7toOVF2E02WA8ubf8pG` | LLM API密钥 |
| `LLM_API_BASE` | `https://api.chatanywhere.tech/v1` | LLM API地址 |
| `LLM_MODEL` | `gpt-4o-mini` | LLM模型名称 |

---

## 📋 批量配置方法

### 方法1: JSON格式（推荐）

华为云支持通过JSON批量导入环境变量：

#### video-vault-slicer.json
```json
{
  "HUAWEI_CLOUD_AK": "HPUACBZNVJEWFWDF8ZEW",
  "HUAWEI_CLOUD_SK": "PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu",
  "HUAWEI_CLOUD_REGION": "cn-north-4",
  "OBS_BUCKET_NAME": "video-vault-storage",
  "SLICE_DURATION": "30",
  "DLP_SCANNER_FUNCTION_URN": "urn:fss:cn-north-4:96c5e3fa586c486e977707f516a95e4d:function:default:video-vault-dlp-scanner:latest"
}
```

#### video-vault-dlp-scanner.json
```json
{
  "HUAWEI_CLOUD_AK": "HPUACBZNVJEWFWDF8ZEW",
  "HUAWEI_CLOUD_SK": "PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu",
  "HUAWEI_CLOUD_REGION": "cn-north-4",
  "OBS_BUCKET_NAME": "video-vault-storage",
  "OCR_PROJECT_ID": "96c5e3fa586c486e977707f516a95e4d",
  "OCR_CONFIDENCE_THRESHOLD": "0.6",
  "BLUR_INTENSITY": "30",
  "VIDEO_MERGER_FUNCTION_URN": "urn:fss:cn-north-4:96c5e3fa586c486e977707f516a95e4d:function:default:video-vault-merger:latest"
}
```

#### video-vault-merger.json
```json
{
  "HUAWEI_CLOUD_AK": "HPUACBZNVJEWFWDF8ZEW",
  "HUAWEI_CLOUD_SK": "PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu",
  "HUAWEI_CLOUD_REGION": "cn-north-4",
  "OBS_BUCKET_NAME": "video-vault-storage"
}
```

#### video-vault-ai-agent.json
```json
{
  "HUAWEI_CLOUD_AK": "HPUACBZNVJEWFWDF8ZEW",
  "HUAWEI_CLOUD_SK": "PbWhb5d8sqHoo2eKnZsKk4xUrstK1lykqmy4XkHu",
  "HUAWEI_CLOUD_REGION": "cn-north-4",
  "OBS_BUCKET_NAME": "video-vault-storage",
  "LLM_API_KEY": "sk-B2WnTcrxS5MzRvNngtoy9NtSDq4Yt7toOVF2E02WA8ubf8pG",
  "LLM_API_BASE": "https://api.chatanywhere.tech/v1",
  "LLM_MODEL": "gpt-4o-mini"
}
```

### 如何使用JSON导入？

1. 进入函数页面
2. 点击 **配置** 标签
3. 滚动到 **环境变量** 部分
4. 点击 **编辑**
5. 如果支持JSON导入，粘贴对应的JSON
6. 如果不支持，手动逐个添加

---

## ⚠️ 注意事项

### 1. 必须配置的变量（所有函数）
```
HUAWEI_CLOUD_AK
HUAWEI_CLOUD_SK
HUAWEI_CLOUD_REGION
OBS_BUCKET_NAME
```

**如果这4个变量缺失，函数会报错：**
```
KeyError: 'HUAWEI_CLOUD_AK'
或
Config error: Missing required environment variable
```

### 2. Function URN 必须在创建函数后配置

**操作顺序：**
1. 先创建所有4个函数（不配置URN）
2. 然后逐个进入函数，复制URN
3. 回到 slicer 和 dlp-scanner 函数，配置URN环境变量
4. 保存配置

### 3. 项目ID 如何获取？

**方法1**: 从浏览器地址栏获取
```
https://console.huaweicloud.com/functiongraph/?region=cn-north-4#/serverless/functions/detail/cn-north-4/96c5e3fa586c486e977707f516a95e4d/...
                                                                                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                                                                        这就是项目ID
```

**方法2**: 我的凭证页面
1. 进入控制台右上角 → **我的凭证**
2. 找到 **API凭证** → **项目列表**
3. 找到 `cn-north-4` 对应的项目ID

---

## 🔍 检查配置是否生效

### 测试方法
在函数的 **测试** 标签页，添加测试代码：

```python
import os
import json

def handler(event, context):
    env_vars = {
        'HUAWEI_CLOUD_AK': os.getenv('HUAWEI_CLOUD_AK', 'NOT SET'),
        'HUAWEI_CLOUD_SK': os.getenv('HUAWEI_CLOUD_SK', 'NOT SET')[:10] + '...',
        'HUAWEI_CLOUD_REGION': os.getenv('HUAWEI_CLOUD_REGION', 'NOT SET'),
        'OBS_BUCKET_NAME': os.getenv('OBS_BUCKET_NAME', 'NOT SET'),
    }

    return {
        'statusCode': 200,
        'body': json.dumps(env_vars, indent=2)
    }
```

点击 **测试**，如果看到：
```json
{
  "HUAWEI_CLOUD_AK": "HPUAC...",
  "HUAWEI_CLOUD_SK": "PbWhb5d8sq...",
  "HUAWEI_CLOUD_REGION": "cn-north-4",
  "OBS_BUCKET_NAME": "video-vault-storage"
}
```
说明配置成功！

---

## 🐛 常见错误

### 错误1: KeyError
```
KeyError: 'HUAWEI_CLOUD_AK'
```
**原因**: 环境变量未配置
**解决**: 在函数配置中添加该变量

### 错误2: InvalidCredentials
```
obs.client.error: InvalidCredentials
```
**原因**: AK/SK错误
**解决**: 检查是否有多余空格，重新复制粘贴

### 错误3: Function URN not found
```
Function urn:fss:... not found
```
**原因**: URN配置错误或函数未创建
**解决**: 确认被调用的函数���创建，URN完整且正确

---

## 📝 配置完成后的验证清单

- [ ] `video-vault-slicer` 已配置 AK/SK/REGION/BUCKET/DLP_SCANNER_URN
- [ ] `video-vault-dlp-scanner` 已配置 AK/SK/REGION/BUCKET/OCR_PROJECT_ID/MERGER_URN
- [ ] `video-vault-merger` 已配置 AK/SK/REGION/BUCKET
- [ ] `video-vault-ai-agent` 已配置 AK/SK/REGION/BUCKET/LLM相关
- [ ] 所有URN都是从对应函数页面复制的完整URN
- [ ] 运行测试代码验证环境变量已生效

配置完成后，重新上传视频测试！
