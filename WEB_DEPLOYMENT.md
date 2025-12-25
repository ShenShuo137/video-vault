# Video Vault Web 界面部署指南

## 架构说明

```
video-vault/
├── backend/           # Flask后端API (Python)
│   ├── app.py        # API服务器
│   └── uploads/      # 上传文件目录
└── frontend/         # Vue 3前端
    ├── src/
    │   ├── views/    # 页面组件
    │   ├── components/  # UI组件
    │   └── api/      # API调用
    └── package.json
```

## 快速开始

### 第1步: 创建Vue 3前端项目

在项目根目录（video-vault/）执行：

```bash
# 使用Vite创建Vue 3项目
npm create vite@latest frontend -- --template vue

# 进入前端目录
cd frontend

# 安装依赖
npm install

# 安装UI库和工具
npm install axios element-plus @element-plus/icons-vue
npm install vue-router@4 pinia
```

### 第2步: 配置前端项目

创建以下文件来配置前端项目。

#### 2.1 配置API基础URL

创建 `frontend/src/api/config.js`:

```javascript
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000',
  timeout: 60000,
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    const message = error.response?.data?.error || error.message || '请求失败'
    console.error('API Error:', message)
    return Promise.reject(error)
  }
)

export default api
```

#### 2.2 创建API服务

创建 `frontend/src/api/video.js`:

```javascript
import api from './config'

export const videoAPI = {
  // 健康检查
  healthCheck() {
    return api.get('/api/health')
  },

  // 上传视频
  uploadVideo(file, onProgress) {
    const formData = new FormData()
    formData.append('file', file)

    return api.post('/api/videos/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      }
    })
  },

  // 获取视频列表
  getVideos(params) {
    return api.get('/api/videos', { params })
  },

  // 获取视频详情
  getVideoDetail(videoId) {
    return api.get(`/api/videos/${videoId}`)
  },

  // 下载视频
  downloadVideo(videoId) {
    return `${api.defaults.baseURL}/api/videos/${videoId}/download`
  },

  // 获取审计日志
  getAuditLogs(params) {
    return api.get('/api/audit/logs', { params })
  },

  // 获取审计统计
  getAuditStats(days = 7) {
    return api.get('/api/audit/stats', { params: { days } })
  },

  // AI对话
  aiChat(message) {
    return api.post('/api/ai/chat', { message })
  },

  // 重置AI对话
  aiReset() {
    return api.post('/api/ai/reset')
  },

  // 获取仪表盘数据
  getDashboard() {
    return api.get('/api/stats/dashboard')
  }
}
```

#### 2.3 配置路由

创建 `frontend/src/router/index.js`:

```javascript
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue')
  },
  {
    path: '/videos',
    name: 'Videos',
    component: () => import('../views/Videos.vue')
  },
  {
    path: '/upload',
    name: 'Upload',
    component: () => import('../views/Upload.vue')
  },
  {
    path: '/audit',
    name: 'Audit',
    component: () => import('../views/Audit.vue')
  },
  {
    path: '/ai-assistant',
    name: 'AIAssistant',
    component: () => import('../views/AIAssistant.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

#### 2.4 修改 `frontend/src/main.js`:

```javascript
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// 注册所有图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus)
app.use(router)
app.mount('#app')
```

### 第3步: 创建页面组件

我会为你生成关键页面的代码。将这些文件放在 `frontend/src/views/` 目录下。

#### 3.1 主应用布局 `frontend/src/App.vue`:

```vue
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
```

### 第4步: 运行项目

#### 启动后端（在项目根目录）:

```bash
# 确保已安装Python依赖
pip install Flask Flask-CORS

# 运行后端
python backend/app.py
```

后端将在 `http://127.0.0.1:5000` 运行

#### 启动前端（在frontend目录）:

```bash
cd frontend
npm run dev
```

前端将在 `http://localhost:5173` 运行

### 第5步: 测试

1. 打开浏览器访问 `http://localhost:5173`
2. 你应该看到Video Vault的界面
3. 点击"上传视频"上传测试视频
4. 查看处理进度和结果

## 页面说明

1. **仪表盘** - 显示统计数据和最近活动
2. **上传视频** - 上传视频进行DLP处理
3. **视频列表** - 查看所有处理过的视频
4. **审计日志** - 查看敏感信息检测记录
5. **AI助手** - 与AI安全助手对话

## 下一步

我可以帮你创建完整的页面组件代码。需要我继续吗？
