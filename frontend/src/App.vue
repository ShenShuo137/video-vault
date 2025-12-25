<template>
  <el-container class="app-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <h2>🔒 Video Vault</h2>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#545c64"
        text-color="#fff"
        active-text-color="#ffd04b"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/upload">
          <el-icon><Upload /></el-icon>
          <span>上传视频</span>
        </el-menu-item>
        <el-menu-item index="/videos">
          <el-icon><VideoCamera /></el-icon>
          <span>视频列表</span>
        </el-menu-item>
        <el-menu-item index="/audit">
          <el-icon><Document /></el-icon>
          <span>审计日志</span>
        </el-menu-item>
        <el-menu-item index="/ai-assistant">
          <el-icon><ChatDotRound /></el-icon>
          <span>AI助手</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <h3>企业会议视频智能安全平台</h3>
        <div class="status">
          <el-tag :type="serverStatus === 'ok' ? 'success' : 'danger'">
            {{ serverStatus === 'ok' ? '在线' : '离线' }}
          </el-tag>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view></router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { videoAPI } from './api/video'

const serverStatus = ref('checking')

onMounted(async () => {
  try {
    await videoAPI.healthCheck()
    serverStatus.value = 'ok'
  } catch (error) {
    serverStatus.value = 'error'
  }
})
</script>

<style scoped>
.app-container {
  height: 100vh;
}

.sidebar {
  background-color: #545c64;
}

.logo {
  padding: 20px;
  text-align: center;
  color: #fff;
  border-bottom: 1px solid #434a50;
}

.logo h2 {
  margin: 0;
  font-size: 18px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>