# 完全Serverless架构 - 前端改造指南

> 移除Flask后端，前端直接操作OBS，实现完全serverless

---

## 📊 架构对比

### ❌ 旧架构（需要后端服务器）

```
前端 Vue.js
    ↓ HTTP API
Flask后端 (python app.py) ← 需要手动启动！
    ↓ 调用本地代码
VideoVaultPipeline
    ↓
3个云函数 (已部署华为云)
```

### ✅ 新架构（完全Serverless）

```
前端 Vue.js (OBS静态托管)
    ↓ 直接上传
OBS存储桶 (uploads/)
    ↓ 触发器
云函数自动处理
    ↓ 输出
OBS存储桶 (outputs/)
    ↑ 前端查询
前端轮询获取结果
```

---

## 🔄 需要修改的部分

### 1. 前端修改（核心改动）

#### 修改文件：`frontend/src/api/obs-client.js` (新建)

创建OBS客户端，用于直接上传和查询：

```javascript
import { ObsClient } from 'esdk-obs-browserjs'

// OBS配置（从环境变量读取）
const OBS_CONFIG = {
  access_key_id: import.meta.env.VITE_HUAWEI_CLOUD_AK,
  secret_access_key: import.meta.env.VITE_HUAWEI_CLOUD_SK,
  server: 'https://obs.cn-north-4.myhuaweicloud.com'
}

const BUCKET_NAME = import.meta.env.VITE_OBS_BUCKET_NAME || 'video-vault-storage'

// 初始化OBS客户端
let obsClient = null

export function initOBS() {
  if (!obsClient) {
    obsClient = new ObsClient({
      access_key_id: OBS_CONFIG.access_key_id,
      secret_access_key: OBS_CONFIG.secret_access_key,
      server: OBS_CONFIG.server
    })
  }
  return obsClient
}

// 上传视频到OBS
export async function uploadVideoToOBS(file, onProgress) {
  const client = initOBS()
  const videoId = `${Date.now()}-${file.name.replace(/\.[^/.]+$/, '')}`
  const objectKey = `uploads/${videoId}.mp4`

  return new Promise((resolve, reject) => {
    client.putObject({
      Bucket: BUCKET_NAME,
      Key: objectKey,
      SourceFile: file,
      ProgressCallback: (transferredAmount, totalAmount) => {
        const percent = Math.round((transferredAmount / totalAmount) * 100)
        if (onProgress) onProgress(percent)
      }
    }, (err, result) => {
      if (err) {
        console.error('上传失败:', err)
        reject(err)
      } else {
        console.log('上传成功:', result)
        resolve({ videoId, objectKey })
      }
    })
  })
}

// 查询处理状态（检查outputs目录是否有结果）
export async function checkVideoStatus(videoId) {
  const client = initOBS()
  const outputKey = `outputs/${videoId}_sanitized.mp4`

  return new Promise((resolve) => {
    client.getObjectMetadata({
      Bucket: BUCKET_NAME,
      Key: outputKey
    }, (err, result) => {
      if (err) {
        if (err.code === 'NoSuchKey') {
          // 文件还不存在，处理中
          resolve({ status: 'processing', exists: false })
        } else {
          resolve({ status: 'error', error: err })
        }
      } else {
        // 文件存在，处理完成
        resolve({
          status: 'completed',
          exists: true,
          size: result.InterfaceResult.ContentLength,
          lastModified: result.InterfaceResult.LastModified
        })
      }
    })
  })
}

// 获取视频下载URL
export function getVideoDownloadURL(videoId) {
  const client = initOBS()
  const outputKey = `outputs/${videoId}_sanitized.mp4`

  return new Promise((resolve, reject) => {
    client.createSignedUrlSync({
      Method: 'GET',
      Bucket: BUCKET_NAME,
      Key: outputKey,
      Expires: 3600  // 1小时有效期
    }, (err, result) => {
      if (err) {
        reject(err)
      } else {
        resolve(result.SignedUrl)
      }
    })
  })
}

// 列出所有处理完成的视频
export async function listProcessedVideos() {
  const client = initOBS()

  return new Promise((resolve, reject) => {
    client.listObjects({
      Bucket: BUCKET_NAME,
      Prefix: 'outputs/',
      MaxKeys: 100
    }, (err, result) => {
      if (err) {
        reject(err)
      } else {
        const videos = result.InterfaceResult.Contents
          .filter(obj => obj.Key.endsWith('_sanitized.mp4'))
          .map(obj => ({
            videoId: obj.Key.replace('outputs/', '').replace('_sanitized.mp4', ''),
            key: obj.Key,
            size: obj.Size,
            lastModified: obj.LastModified
          }))
        resolve(videos)
      }
    })
  })
}

// 获取审计日志（从OBS读取JSON）
export async function getAuditLog(videoId) {
  const client = initOBS()
  const logKey = `logs/${videoId}_audit.json`

  return new Promise((resolve, reject) => {
    client.getObject({
      Bucket: BUCKET_NAME,
      Key: logKey
    }, (err, result) => {
      if (err) {
        if (err.code === 'NoSuchKey') {
          resolve(null)  // 没有审计日志
        } else {
          reject(err)
        }
      } else {
        const content = result.InterfaceResult.Content.toString('utf-8')
        resolve(JSON.parse(content))
      }
    })
  })
}
```

---

#### 修改文件：`frontend/src/api/video.js`

替换Flask API调用为OBS直接操作：

```javascript
import {
  uploadVideoToOBS,
  checkVideoStatus,
  getVideoDownloadURL,
  listProcessedVideos,
  getAuditLog
} from './obs-client'

export const videoAPI = {
  // 上传视频（改为直接上传OBS）
  async uploadVideo(file, onProgress) {
    try {
      const result = await uploadVideoToOBS(file, onProgress)

      // 开始轮询检查状态
      return {
        success: true,
        video_id: result.videoId,
        message: '视频已上传，正在处理...'
      }
    } catch (error) {
      throw new Error('上传失败: ' + error.message)
    }
  },

  // 检查视频处理状态
  async getVideoStatus(videoId) {
    return await checkVideoStatus(videoId)
  },

  // 获取视频列表（从OBS读取）
  async getVideos() {
    const videos = await listProcessedVideos()
    return { videos, total: videos.length }
  },

  // 获取视频详情
  async getVideoDetail(videoId) {
    const status = await checkVideoStatus(videoId)
    const auditLog = await getAuditLog(videoId)

    return {
      video_id: videoId,
      status: status.status,
      audit_log: auditLog,
      size: status.size,
      last_modified: status.lastModified
    }
  },

  // 获取下载URL
  async downloadVideo(videoId) {
    return await getVideoDownloadURL(videoId)
  },

  // 获取审计日志
  async getAuditLogs(videoId) {
    if (videoId) {
      const log = await getAuditLog(videoId)
      return { logs: log?.detections || [], total: log?.detections?.length || 0 }
    } else {
      // 获取所有视频的审计日志
      const videos = await listProcessedVideos()
      const allLogs = []

      for (const video of videos) {
        const log = await getAuditLog(video.videoId)
        if (log) {
          allLogs.push(...log.detections.map(d => ({
            ...d,
            video_id: video.videoId
          })))
        }
      }

      return { logs: allLogs, total: allLogs.length }
    }
  },

  // 健康检查（检查OBS连接）
  async healthCheck() {
    try {
      await listProcessedVideos()
      return { status: 'ok', mode: 'serverless' }
    } catch (error) {
      return { status: 'error', error: error.message }
    }
  }
}
```

---

### 2. 云函数修改（保存审计日志到OBS）

#### 修改文件：`functions/dlp_scanner_handler.py`

在line 105后添加，将审计日志保存到OBS：

```python
# 上传处理后的切片
processed_key = f"processed/{video_id}/slice_{slice_index:04d}.mp4"
obs_helper.upload_file(processed_slice_path, processed_key)

# ✅ 新增：保存审计日志到OBS（供前端查询）
if slice_index == 0:  # 只在第一个切片时创建日志文件
    audit_log_data = {
        'video_id': video_id,
        'detections': [],
        'total_detections': 0
    }
    audit_log_json = json.dumps(audit_log_data, ensure_ascii=False)
    audit_log_key = f"logs/{video_id}_audit.json"

    # 上传空的审计日志文件
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(audit_log_json)
        temp_path = f.name
    obs_helper.upload_file(temp_path, audit_log_key)
    os.remove(temp_path)

# 追加审计记录到日志文件（每个切片）
for result in scan_results:
    for detection in result['scan_result']['detections']:
        audit_entry = {
            'slice_index': slice_index,
            'frame_id': result['frame_id'],
            'timestamp': result['timestamp'],
            'type': detection['sensitive_type'],
            'text': detection['ocr_text'][:100],
            'confidence': detection['ocr_confidence'],
            'bbox': {
                'x': detection['bbox'][0],
                'y': detection['bbox'][1],
                'width': detection['bbox'][2],
                'height': detection['bbox'][3]
            }
        }

        # 下载现有日志
        audit_log_key = f"logs/{video_id}_audit.json"
        temp_log = f"/tmp/audit_{video_id}.json"
        obs_helper.download_file(audit_log_key, temp_log)

        # 更新日志
        with open(temp_log, 'r') as f:
            audit_data = json.load(f)
        audit_data['detections'].append(audit_entry)
        audit_data['total_detections'] = len(audit_data['detections'])

        # 上传更新后的日志
        with open(temp_log, 'w') as f:
            json.dump(audit_data, f, ensure_ascii=False)
        obs_helper.upload_file(temp_log, audit_log_key)
        os.remove(temp_log)
```

---

### 3. 环境变量配置

#### 前端：`frontend/.env`

```bash
# 华为云配置
VITE_HUAWEI_CLOUD_AK=your_access_key
VITE_HUAWEI_CLOUD_SK=your_secret_key
VITE_OBS_BUCKET_NAME=video-vault-storage
VITE_OBS_ENDPOINT=https://obs.cn-north-4.myhuaweicloud.com
```

---

### 4. 前端组件修改示例

#### 上传组件修改

```vue
<script setup>
import { videoAPI } from '@/api/video'
import { ref } from 'vue'

const uploading = ref(false)
const progress = ref(0)
const videoId = ref(null)
const processingStatus = ref('idle')  // idle, uploading, processing, completed

async function handleUpload(file) {
  try {
    uploading.value = true
    processingStatus.value = 'uploading'

    // 直接上传到OBS
    const result = await videoAPI.uploadVideo(file, (percent) => {
      progress.value = percent
    })

    videoId.value = result.video_id
    processingStatus.value = 'processing'

    // 开始轮询检查状态
    pollStatus()

  } catch (error) {
    console.error('上传失败:', error)
    processingStatus.value = 'idle'
  } finally {
    uploading.value = false
  }
}

async function pollStatus() {
  const maxAttempts = 60  // 最多查询5分钟
  let attempts = 0

  const interval = setInterval(async () => {
    attempts++

    const status = await videoAPI.getVideoStatus(videoId.value)

    if (status.status === 'completed') {
      processingStatus.value = 'completed'
      clearInterval(interval)
      // 显示成功提示
    } else if (attempts >= maxAttempts) {
      processingStatus.value = 'timeout'
      clearInterval(interval)
      // 显示超时提示
    }
  }, 5000)  // 每5秒查询一次
}
</script>
```

---

## 📦 前端依赖安装

```bash
cd frontend
npm install esdk-obs-browserjs
```

---

## 🚀 部署步骤

### 步骤1: 部署云函数（已完成）

按照之前的 `DEPLOYMENT_QUICK_START.md` 部署3个云函数。

### 步骤2: 配置CORS（重要！）

在华为云OBS控制台配置跨域规则：

1. 进入OBS控制台 → 选择bucket `video-vault-storage`
2. 点击 **基础配置** → **跨域资源共享(CORS)**
3. 添加规则：
   ```
   允许的来源: * (或你的前端域名)
   允许的方法: GET, PUT, POST, DELETE, HEAD
   允许的头部: *
   暴露的头部: ETag, x-obs-request-id
   缓存时间: 3600
   ```

### 步骤3: 部署前端到OBS静态托管

```bash
# 1. 构建前端
cd frontend
npm run build

# 2. 上传到OBS
# 方式A: 使用OBS浏览器控制台手动上传dist目录
# 方式B: 使用obsutil命令行工具
obsutil cp -r dist/ obs://video-vault-storage/website/ -f
```

### 步骤4: 配置OBS静态网站托管

1. OBS控制台 → bucket → **静态网站托管**
2. 启用静态网站托管
3. 默认首页: `index.html`
4. 404错误页面: `index.html`（支持Vue Router）
5. 获取访问域名: `http://video-vault-storage.obs-website.cn-north-4.myhuaweicloud.com`

---

## ✅ 优势

1. **0运维成本**：无需服务器，无需关心运维
2. **自动扩缩容**：并发自动扩展，处理能力无上限
3. **按需付费**：只为实际使用的资源付费
4. **高可用性**：华为云保障99.95%可用性
5. **快速部署**：前端静态文件，秒级部署

---

## 💰 成本估算

### Serverless成本（月）

| 服务 | 用量 | 单价 | 费用 |
|------|------|------|------|
| OBS存储 | 100GB | ¥0.099/GB | ¥9.9 |
| OBS流量 | 50GB | ¥0.50/GB | ¥25 |
| 云函数调用 | 10万次 | ¥0.0133/千次 | ¥1.33 |
| 云函数执行时长 | 10万GB秒 | ¥0.00011108/GB秒 | ¥11.1 |
| OCR识别 | 1000次 | ¥1/千次 | ¥1 |
| **合计** | | | **¥48.33** |

### 传统服务器成本（月）

| 服务 | 配置 | 费用 |
|------|------|------|
| 云服务器 | 2核4G | ¥200+ |
| 带宽 | 5Mbps | ¥50+ |
| **合计** | | **¥250+** |

**节省成本约80%！** 🎉

---

## 🆚 架构对比

| 对比项 | Flask后端 | Serverless |
|--------|-----------|------------|
| 服务器 | 需要 | 不需要 ✅ |
| 运维 | 需要手动启动/监控 | 0运维 ✅ |
| 扩展性 | 手动扩容 | 自动扩展 ✅ |
| 成本 | 固定成本高 | 按需付费 ✅ |
| 可用性 | 单点故障风险 | 高可用 ✅ |
| 冷启动 | 无 | 有(~2秒) |

---

## ❓ 常见问题

### Q: 前端如何知道视频处理完成？

**A**: 轮询查询OBS，检查`outputs/`目录是否有结果文件。

### Q: 如果处理失败怎么办？

**A**:
1. 云函数会记录错误日志到FunctionGraph
2. 可以在云函数中添加错误通知（发送到OBS或外部API）
3. 前端超时后提示用户

### Q: 能否保留Flask后端？

**A**:
- **可以**，但这样就不是完全serverless了
- 如果需要复杂的后端逻辑，可以使用**API Gateway + 云函数**替代Flask

### Q: 审计日志如何查询？

**A**:
- 方案1: 保存到OBS，前端直接读取JSON（已实现）
- 方案2: 使用RDS数据库，通过API Gateway查询

### Q: AI Agent功能怎么办？

**A**:
- 创建单独的AI Agent云函数
- 通过API Gateway暴露HTTP接口
- 前端调用API Gateway

---

## 🎉 总结

完全Serverless架构：
- ✅ **前端**：OBS静态托管
- ✅ **后端**：无需手动启动
- ✅ **处理**：云函数自动触发
- ✅ **存储**：OBS对象存储
- ✅ **成本**：降低80%
- ✅ **运维**：0人工维护

**Flask `backend/app.py` 可以完全删除！** 🎊
