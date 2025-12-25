<template>
  <div class="videos-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>视频列表</span>
          <div>
            <el-button type="primary" @click="loadVideos">刷新</el-button>
            <el-popconfirm
              title="确定要清空所有数据吗？此操作不可恢复！"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="clearAllData"
            >
              <template #reference>
                <el-button type="danger" :loading="clearing">清空数据</el-button>
              </template>
            </el-popconfirm>
          </div>
        </div>
      </template>

      <el-table :data="videos" v-loading="loading" style="width: 100%">
        <el-table-column prop="video_id" label="视频ID" width="280" />
        <el-table-column prop="filename" label="文件名" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="getStatusType(scope.row.status)">
              {{ getStatusText(scope.row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button
              size="small"
              type="primary"
              @click="downloadVideo(scope.row.video_id)"
            >
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="videos.length === 0 && !loading" description="暂无视频" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { videoAPI } from '../api/video'
import { ElMessage } from 'element-plus'

const videos = ref([])
const loading = ref(false)
const clearing = ref(false)

const loadVideos = async () => {
  loading.value = true
  try {
    const data = await videoAPI.getVideos()
    videos.value = data.videos || []
  } catch (error) {
    ElMessage.error('加载视频列表失败')
  } finally {
    loading.value = false
  }
}

const downloadVideo = async (videoId) => {
  try {
    const url = await videoAPI.downloadVideo(videoId)
    window.open(url, '_blank')
  } catch (error) {
    ElMessage.error('获取下载链接失败')
  }
}

const clearAllData = async () => {
  clearing.value = true
  try {
    // Serverless架构：删除OBS中的所有文件
    ElMessage.warning('Serverless架构下暂不支持批量清空，请在OBS控制台手动删除')
    // TODO: 可以实现遍历OBS并删除所有文件，但需要谨慎操作
  } catch (error) {
    ElMessage.error('操作失败: ' + error.message)
  } finally {
    clearing.value = false
  }
}

const getStatusType = (status) => {
  const typeMap = {
    uploading: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

const getStatusText = (status) => {
  const textMap = {
    uploading: '上传中',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return textMap[status] || status
}

onMounted(() => {
  loadVideos()
})
</script>

<style scoped>
.videos-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header > div {
  display: flex;
  gap: 10px;
}
</style>
