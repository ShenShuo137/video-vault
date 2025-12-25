<template>
  <div class="upload-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>上传视频</span>
        </div>
      </template>

      <el-upload
        ref="uploadRef"
        class="upload-demo"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept="video/*"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽视频文件到此处 或 <em>点击选择</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 mp4, avi, mov, mkv 等格式，最大500MB
          </div>
        </template>
      </el-upload>

      <div v-if="selectedFile" class="file-info">
        <el-descriptions title="文件信息" :column="2" border>
          <el-descriptions-item label="文件名">{{ selectedFile.name }}</el-descriptions-item>
          <el-descriptions-item label="大小">{{ formatFileSize(selectedFile.size) }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ selectedFile.type }}</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="upload-actions">
        <el-button
          type="primary"
          size="large"
          :disabled="!selectedFile || uploading"
          :loading="uploading"
          @click="handleUpload"
        >
          {{ uploading ? '处理中...' : '开始处理' }}
        </el-button>
        <el-button size="large" @click="handleClear">清空</el-button>
      </div>

      <div v-if="uploading" class="progress-section">
        <el-progress
          :percentage="uploadProgress"
          :status="uploadProgress === 100 ? 'success' : undefined"
        />
        <p class="progress-tip">{{ progressText }}</p>
      </div>

      <el-alert
        v-if="uploadResult"
        :type="uploadResult.success ? 'success' : 'error'"
        :title="uploadResult.success ? '处理完成' : '处理失败'"
        :closable="false"
        show-icon
        style="margin-top: 20px;"
      >
        <template v-if="uploadResult.success">
          <p>视频ID: {{ uploadResult.video_id }}</p>
          <p>检测到敏感信息: {{ uploadResult.sensitive_count }} 个</p>
          <el-button
            type="success"
            size="small"
            @click="downloadVideo"
            style="margin-top: 10px;"
          >
            下载处理后的视频
          </el-button>
        </template>
        <template v-else>
          <p>{{ uploadResult.error }}</p>
        </template>
      </el-alert>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { videoAPI } from '../api/video'
import { ElMessage } from 'element-plus'

const uploadRef = ref()
const selectedFile = ref(null)
const uploading = ref(false)
const uploadProgress = ref(0)
const progressText = ref('')
const uploadResult = ref(null)

const handleFileChange = (file) => {
  selectedFile.value = file.raw
  uploadResult.value = null
}

const handleClear = () => {
  selectedFile.value = null
  uploadProgress.value = 0
  uploadResult.value = null
  uploadRef.value.clearFiles()
}

const handleUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }

  uploading.value = true
  uploadProgress.value = 0
  progressText.value = '上传中...'
  uploadResult.value = null

  try {
    // 1. 上传到OBS
    const result = await videoAPI.uploadVideo(selectedFile.value, (percent) => {
      uploadProgress.value = Math.min(percent, 50)
    })

    uploadProgress.value = 60
    progressText.value = '上传完成，云函数处理中...'

    console.log('===== 上传完成，开始追踪云函数处理 =====')
    console.log('视频ID:', result.video_id)
    console.log('OBS对象键:', result.object_key)
    console.log('等待OBS触发器启动云函数...')

    // 2. 轮询查询处理状态
    const videoId = result.video_id
    let processingComplete = false
    let attempts = 0
    const maxAttempts = 60  // 最多等待5分钟 (60 * 5秒)

    while (!processingComplete && attempts < maxAttempts) {
      attempts++
      uploadProgress.value = 60 + Math.min((attempts / maxAttempts) * 35, 35)

      console.log(`\n[轮询 ${attempts}/${maxAttempts}] 检查处理状态...`)

      await new Promise(resolve => setTimeout(resolve, 5000))  // 等待5秒

      try {
        const status = await videoAPI.getVideoStatus(videoId)
        console.log('状态查询结果:', JSON.stringify(status, null, 2))

        // 根据详细状态更新进度文本
        if (status.details) {
          const stage = status.details.stage
          if (stage === 'slicing') {
            progressText.value = `等待云函数启动... (${attempts}/${maxAttempts})`
          } else if (stage === 'scanning') {
            progressText.value = `DLP扫描中 (已生成 ${status.details.slices_found} 个切片) (${attempts}/${maxAttempts})`
          } else if (stage === 'merging') {
            progressText.value = `正在合并视频... (${attempts}/${maxAttempts})`
          }
        }

        if (status.status === 'completed') {
          console.log('✅ 视频处理完成！')
          processingComplete = true

          // 3. 查询详细信息（包括敏感信息数量）
          console.log('正在获取审计日志...')
          const detail = await videoAPI.getVideoDetail(videoId)
          console.log('审计详情:', JSON.stringify(detail, null, 2))

          uploadProgress.value = 100
          progressText.value = '处理完成!'
          uploadResult.value = {
            success: true,
            video_id: videoId,
            sensitive_count: detail.sensitive_count || 0
          }
          ElMessage.success('视频处理完成!')
        } else if (status.status === 'error') {
          console.error('❌ 云函数处理失败:', status.error)
          throw new Error('云函数处理失败: ' + (status.error || '未知错误'))
        } else if (status.status === 'processing') {
          console.log('⏳ 仍在处理中...')
        } else {
          console.log('⚠️ 未知状态:', status.status)
          if (!status.details) {
            progressText.value = `等待云函数启动... (${attempts}/${maxAttempts})`
          }
        }
      } catch (err) {
        console.error('❌ 查询状态失败:', err)
        progressText.value = `查询失败，继续等待... (${attempts}/${maxAttempts})`
      }
    }

    if (!processingComplete) {
      uploadProgress.value = 100
      progressText.value = '处理超时，请稍后在视频列表中查看'
      uploadResult.value = {
        success: true,
        video_id: videoId,
        sensitive_count: 0,
        note: '处理可能需要更长时间，请稍后查看'
      }
      ElMessage.warning('处理时间较长，请稍后在视频列表中查看结果')
    }

  } catch (error) {
    uploadResult.value = {
      success: false,
      error: error.response?.data?.error || error.message || '上传失败'
    }
    ElMessage.error('视频处理失败')
  } finally {
    uploading.value = false
  }
}

const downloadVideo = async () => {
  try {
    const url = await videoAPI.downloadVideo(uploadResult.value.video_id)
    window.open(url, '_blank')
  } catch (error) {
    ElMessage.error('获取下载链接失败')
  }
}

const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}
</script>

<style scoped>
.upload-page {
  padding: 20px;
}

.upload-demo {
  margin: 20px 0;
}

.file-info {
  margin: 20px 0;
}

.upload-actions {
  margin: 20px 0;
  text-align: center;
}

.progress-section {
  margin-top: 20px;
}

.progress-tip {
  text-align: center;
  margin-top: 10px;
  color: #909399;
}
</style>
