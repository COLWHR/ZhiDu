<template>
  
  <a-layout style="min-height: 100vh">
    <a-layout-sider
      v-model:collapsed="collapsed"
      collapsible
      theme="light"
      breakpoint="lg"
      :width="240"
      class="sider-layout"
    >
      <div class="logo">
        <img src="@/assets/logo.png" alt="智渡" class="logo-icon" />
        <span v-if="!collapsed" class="logo-text">智渡</span>
        <span v-else class="logo-text">渡</span>
      </div>
      

      <a-menu :selectedKeys="selectedKeys" theme="light" mode="inline" class="nav-menu">
        <a-menu-item key="dashboard" @click="navigateTo('/dashboard')" class="nav-item">
            <dashboard-outlined class="nav-icon" />
            <span>概览</span>
        </a-menu-item>
        
        <a-menu-item key="personas" @click="navigateTo('/personas')" class="nav-item">
            <team-outlined class="nav-icon" />
            <span>智能体工坊</span>
        </a-menu-item>
        
        <a-menu-item key="forums" @click="navigateTo('/forums')" class="nav-item">
            <comment-outlined class="nav-icon" />
            <span>圆桌论坛</span>
        </a-menu-item>

        <a-menu-item key="assistants" @click="navigateTo('/assistants')" class="nav-item">
            <appstore-outlined class="nav-icon" />
            <span>助手仓库</span>
        </a-menu-item>

        <a-menu-item key="time-gate" @click="navigateTo('/time-gate')" class="nav-item">
            <clock-circle-outlined class="nav-icon" />
            <span>时空之门</span>
        </a-menu-item>

        <div class="menu-divider"></div>
        
        <a-menu-item key="logout" @click="handleLogout" class="nav-item logout-item">
          <logout-outlined class="nav-icon" />
          <span>退出登录</span>
        </a-menu-item>
      </a-menu>
    </a-layout-sider>
    
    <a-layout class="site-layout">
      <a-layout-content class="layout-content">
        <div class="content-wrapper">
          <router-view />
        </div>
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { message } from 'ant-design-vue'
import request from '@/utils/request'
import {
  DashboardOutlined,
  TeamOutlined,
  CommentOutlined,
  AppstoreOutlined,
  ClockCircleOutlined,
  LogoutOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const collapsed = ref(false)

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}

const navigateTo = (path: string) => {
    router.push(path)
}

const selectedKeys = computed(() => {
  if (route.path === '/' || route.path.startsWith('/dashboard')) return ['dashboard']
  if (route.path.startsWith('/personas')) return ['personas']
  if (route.path.startsWith('/forums')) return ['forums']
  if (route.path.startsWith('/assistants')) return ['assistants']
  if (route.path.startsWith('/time-gate')) return ['time-gate']
  return []
})

// 监听登录状态
watch(() => authStore.token, (token) => {
  if (!token) {
    router.push('/login')
  }
}, { immediate: true })
</script>

<style scoped>
.logo {
  height: 64px;
  margin: 20px 16px;
  background: linear-gradient(-225deg, #69EACB 0%, #EACCF8 48%, #6654F1 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-radius: 16px;
  overflow: hidden;
  white-space: nowrap;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}



.logo-icon {
  width: 36px;
  height: 36px;
  object-fit: contain;
  border-radius: 8px;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: white;
}

.sider-layout {
  box-shadow: 4px 0 20px rgba(0, 0, 0, 0.05);
  z-index: 10;
  height: 100vh;
  overflow-y: auto;
  background: linear-gradient(180deg, #ffffff 0%, #f8f9fb 100%);
  border-right: 1px solid #f0f0f0;
}

.nav-menu {
  border: none;
  padding: 8px;
}

.nav-menu :deep(.ant-menu-item) {
  margin: 4px 0;
  border-radius: 10px;
  transition: all 0.3s ease;
}

.nav-menu :deep(.ant-menu-item-selected) {
  background: linear-gradient(135deg, #a6e3e9 0%, #71c9ce 100%);
  color: white;
}

.nav-menu :deep(.ant-menu-item-selected .anticon) {
  color: white;
}

.nav-menu :deep(.ant-menu-item:not(.ant-menu-item-selected):hover) {
  background: #f5f3ff;
  color: #667eea;
}

.nav-icon {
  font-size: 18px;
}

.menu-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, #e8e8e8 50%, transparent 100%);
  margin: 16px 8px;
}

.logout-item {
  margin-top: 8px !important;
}

.logout-item:deep(.anticon),
.logout-item span {
  color: #ff4d4f !important;
}

.logout-item:not(.ant-menu-item-selected):hover {
  background: #fff1f0 !important;
}

.site-layout {
  min-height: 100vh;
  background: #f5f7fa;
}

.layout-content {
  margin: 0;
  padding: 0;
  min-height: 100vh;
  overflow-y: auto;
}

.content-wrapper {
  padding: 0;
  background: transparent;
  min-height: 100vh;
}
</style>
