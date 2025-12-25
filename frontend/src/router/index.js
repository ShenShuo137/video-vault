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