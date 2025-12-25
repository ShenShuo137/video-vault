<template>
  <div class="ai-assistant-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>🤖 AI 安全助手</span>
          <el-button size="small" @click="resetChat">重置对话</el-button>
        </div>
      </template>

      <el-alert
        v-if="!aiAvailable"
        title="AI助手暂不可用"
        type="warning"
        description="请检查华为云配置：VITE_HUAWEI_CLOUD_AK, VITE_HUAWEI_CLOUD_SK, VITE_FUNCTION_PROJECT_ID"
        :closable="false"
        show-icon
        style="margin-bottom: 20px;"
      />

      <div class="chat-container" ref="chatContainer">
        <div v-if="messages.length === 0" class="welcome-message">
          <h3>👋 您好！我是Video Vault的AI安全助手</h3>
          <p>我可以帮您:</p>
          <ul>
            <li>查询审计日志和安全事件</li>
            <li>分析视频中的敏感信息</li>
            <li>列出高风险视频</li>
            <li>生成安全报告</li>
          </ul>
          <p>试试问我: "最近一周检测到了哪些敏感信息?"</p>
        </div>

        <div v-for="(msg, index) in messages" :key="index" class="message-item">
          <div :class="['message', msg.role]">
            <div class="message-avatar">
              {{ msg.role === 'user' ? '👤' : '🤖' }}
            </div>
            <div class="message-content">
              <div class="message-text">{{ msg.content }}</div>
              <div class="message-time">{{ msg.time }}</div>
            </div>
          </div>
        </div>

        <div v-if="loading" class="message-item">
          <div class="message assistant">
            <div class="message-avatar">🤖</div>
            <div class="message-content">
              <el-icon class="is-loading"><Loading /></el-icon>
              思考中...
            </div>
          </div>
        </div>
      </div>

      <div class="input-container">
        <el-input
          v-model="userInput"
          placeholder="输入您的问题..."
          :disabled="!aiAvailable || loading"
          @keyup.enter="sendMessage"
        >
          <template #append>
            <el-button
              :icon="aiAvailable ? 'ChatDotRound' : 'Lock'"
              :disabled="!aiAvailable || loading || !userInput.trim()"
              @click="sendMessage"
            >
              发送
            </el-button>
          </template>
        </el-input>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { videoAPI } from '../api/video'
import { ElMessage } from 'element-plus'

const messages = ref([])
const userInput = ref('')
const loading = ref(false)
const aiAvailable = ref(true)
const chatContainer = ref(null)

const checkAIAvailability = async () => {
  try {
    // 检查必要的环境变量是否配置
    const ak = import.meta.env.VITE_HUAWEI_CLOUD_AK
    const sk = import.meta.env.VITE_HUAWEI_CLOUD_SK
    const projectId = import.meta.env.VITE_FUNCTION_PROJECT_ID

    if (!ak || !sk || !projectId) {
      console.warn('AI Agent配置不完整')
      aiAvailable.value = false
      return
    }

    // 检查OBS配置（作为基础健康检查）
    const health = await videoAPI.healthCheck()
    aiAvailable.value = health.status === 'ok'
  } catch (error) {
    console.error('AI可用性检查失败:', error)
    aiAvailable.value = false
  }
}

const sendMessage = async () => {
  const message = userInput.value.trim()
  if (!message) return

  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: message,
    time: new Date().toLocaleTimeString()
  })

  userInput.value = ''
  loading.value = true

  // 滚动到底部
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })

  try {
    const response = await videoAPI.aiChat(message)

    // 添加AI回复
    messages.value.push({
      role: 'assistant',
      content: response.response,
      time: new Date().toLocaleTimeString()
    })

    // 滚动到底部
    nextTick(() => {
      if (chatContainer.value) {
        chatContainer.value.scrollTop = chatContainer.value.scrollHeight
      }
    })
  } catch (error) {
    // 添加这行，看完整错误
    console.error('AI调用完整错误:', error)
    console.error('错误消息:', error.message)
    console.error('错误堆栈:', error.stack)
  
    ElMessage.error('AI助手暂时无法响应: ' + error.message)
    // ElMessage.error('AI助手暂时无法响应')
  } finally {
    loading.value = false
  }
}

const resetChat = async () => {
  try {
    await videoAPI.aiReset()
    messages.value = []
    ElMessage.success('对话已重置')
  } catch (error) {
    ElMessage.error('重置失败')
  }
}

onMounted(() => {
  checkAIAvailability()
})
</script>

<style scoped>
.ai-assistant-page {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-container {
  height: 500px;
  overflow-y: auto;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 20px;
}

.welcome-message {
  text-align: center;
  color: #909399;
  padding: 50px 20px;
}

.welcome-message h3 {
  margin-bottom: 20px;
  color: #303133;
}

.welcome-message ul {
  text-align: left;
  display: inline-block;
  margin: 20px 0;
}

.welcome-message li {
  margin: 10px 0;
}

.message-item {
  margin-bottom: 20px;
}

.message {
  display: flex;
  align-items: flex-start;
}

.message.user {
  justify-content: flex-end;
}

.message.user .message-content {
  background-color: #409EFF;
  color: white;
}

.message.assistant .message-content {
  background-color: white;
}

.message-avatar {
  font-size: 24px;
  margin: 0 10px;
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.message-text {
  word-wrap: break-word;
  white-space: pre-wrap;
}

.message-time {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.message.user .message-time {
  color: rgba(255, 255, 255, 0.8);
  text-align: right;
}

.input-container {
  position: sticky;
  bottom: 0;
  background-color: white;
  padding-top: 10px;
}
</style>
