<template>
  <div class="dashboard">
    <h1>仪表盘</h1>

    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #409EFF;">
            <el-icon size="30"><VideoCamera /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.total_videos }}</div>
            <div class="stat-label">视频总数</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #67C23A;">
            <el-icon size="30"><Check /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.completed_videos }}</div>
            <div class="stat-label">已完成</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #E6A23C;">
            <el-icon size="30"><Loading /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.processing_videos }}</div>
            <div class="stat-label">处理中</div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-icon" style="background: #F56C6C;">
            <el-icon size="30"><Warning /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.total_sensitive_detections }}</div>
            <div class="stat-label">敏感信息检测</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>最近活动</span>
        </div>
      </template>
      <el-empty v-if="stats.recent_activity.length === 0" description="暂无数据" />
      <el-timeline v-else>
        <el-timeline-item
          v-for="(item, index) in stats.recent_activity"
          :key="index"
          :timestamp="item.detected_time"
        >
          检测到 {{ item.sensitive_type }} ({{ item.video_title }})
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { videoAPI } from '../api/video'
import { ElMessage } from 'element-plus'

const stats = ref({
  total_videos: 0,
  processing_videos: 0,
  completed_videos: 0,
  total_sensitive_detections: 0,
  high_risk_videos: 0,
  recent_activity: []
})

const loadDashboard = async () => {
  try {
    const data = await videoAPI.getDashboard()
    stats.value = data
  } catch (error) {
    ElMessage.error('加载仪表盘数据失败')
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

.stat-card {
  cursor: pointer;
  transition: transform 0.3s;
}

.stat-card:hover {
  transform: translateY(-5px);
}

.stat-card .el-card__body {
  display: flex;
  align-items: center;
  padding: 20px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  margin-right: 20px;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 5px;
}
</style>
