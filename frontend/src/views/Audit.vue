<template>
  <div class="audit-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>审计日志</span>
          <div>
            <el-select v-model="days" @change="loadLogs" style="margin-right: 10px;">
              <el-option label="最近7天" :value="7" />
              <el-option label="最近30天" :value="30" />
              <el-option label="最近90天" :value="90" />
            </el-select>
            <el-button type="primary" @click="loadLogs">刷新</el-button>
          </div>
        </div>
      </template>

      <el-row :gutter="20" style="margin-bottom: 20px;">
        <el-col :span="8">
          <el-statistic title="总检测次数" :value="stats.total_detections" />
        </el-col>
        <el-col :span="16">
          <div class="stats-tags">
            <el-tag
              v-for="(count, type) in stats.by_type"
              :key="type"
              style="margin-right: 10px; margin-bottom: 10px;"
            >
              {{ type }}: {{ count }}
            </el-tag>
          </div>
        </el-col>
      </el-row>

      <el-table :data="logs" v-loading="loading" style="width: 100%">
        <el-table-column prop="video_title" label="视频" width="200" />
        <el-table-column prop="type" label="类型" width="150">
          <template #default="scope">
            <el-tag :type="getSensitiveTypeTag(scope.row.type)">
              {{ scope.row.type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="text" label="检测内容" show-overflow-tooltip />
        <el-table-column prop="confidence" label="置信度" width="100">
          <template #default="scope">
            {{ (scope.row.confidence * 100).toFixed(1) }}%
          </template>
        </el-table-column>
        <el-table-column prop="timestamp" label="时间点(秒)" width="120" />
      </el-table>

      <el-empty v-if="logs.length === 0 && !loading" description="暂无审计日志" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { videoAPI } from '../api/video'
import { ElMessage } from 'element-plus'

const logs = ref([])
const stats = ref({
  total_detections: 0,
  by_type: {},
  period_days: 7
})
const loading = ref(false)
const days = ref(7)

const loadLogs = async () => {
  loading.value = true
  try {
    const [logsData, statsData] = await Promise.all([
      videoAPI.getAuditLogs({ days: days.value }),
      videoAPI.getAuditStats(days.value)
    ])

    logs.value = logsData.logs || []
    stats.value = {
      total_detections: statsData.total_detections || 0,
      by_type: statsData.by_type || {},
      period_days: statsData.period_days || days.value
    }
  } catch (error) {
    console.error('加载审计日志失败:', error)
    ElMessage.error('加载审计日志失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const getSensitiveTypeTag = (type) => {
  const typeMap = {
    openai_key: 'danger',
    aws_key: 'danger',
    huawei_ak: 'danger',
    password: 'danger',
    id_card: 'warning',
    phone: 'warning',
    email: 'info',
    credit_card: 'warning'
  }
  return typeMap[type] || 'info'
}

onMounted(() => {
  loadLogs()
})
</script>

<style scoped>
.audit-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-tags {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}
</style>
