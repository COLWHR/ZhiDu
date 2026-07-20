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
      <div class="logo" :class="{ collapsed }">
        <img src="@/assets/logo.png" alt="智渡" class="logo-icon" />
        <span v-if="!collapsed" class="logo-text">智渡</span>
        <span v-else class="logo-text">智</span>
      </div>
      

      <div class="sider-body">
        <a-menu :selectedKeys="selectedKeys" theme="light" mode="inline" class="nav-menu">
          <a-menu-item key="dashboard" @click="navigateTo('/dashboard')" class="nav-item">
              <dashboard-outlined class="nav-icon" />
              <span>首页</span>
          </a-menu-item>

          <a-menu-item key="personas" @click="navigateTo('/personas')" class="nav-item">
              <team-outlined class="nav-icon" />
              <span>智能体工坊</span>
          </a-menu-item>

          <a-menu-item key="assistants" @click="navigateTo('/assistants')" class="nav-item">
              <appstore-outlined class="nav-icon" />
              <span>助手仓库</span>
          </a-menu-item>

          <a-menu-item key="skills" @click="navigateTo('/assistants/skills')" class="nav-item">
              <tool-outlined class="nav-icon" />
              <span>Skill 仓库</span>
          </a-menu-item>

          <a-menu-item key="time-gate" @click="navigateTo('/time-gate')" class="nav-item">
              <clock-circle-outlined class="nav-icon" />
              <span>时空之门</span>
          </a-menu-item>
        </a-menu>

        <div class="profile-dock">
          <a-popover
            v-model:open="profileOpen"
            trigger="click"
            placement="rightBottom"
            overlayClassName="profile-popover"
          >
            <template #content>
              <div class="profile-panel">
                <div class="profile-panel-header">
                  <a-avatar :size="52" class="profile-panel-avatar">
                    <img v-if="userAvatarSrc" :src="userAvatarSrc" :alt="displayName" />
                    <template v-else>{{ userInitial }}</template>
                  </a-avatar>
                  <div>
                    <div class="profile-panel-name">{{ displayName }}</div>
                    <div class="profile-panel-id">ID {{ userIdLabel }}</div>
                  </div>
                </div>
                <div class="profile-panel-grid">
                  <div>
                    <span>角色</span>
                    <strong>{{ roleLabel }}</strong>
                  </div>
                  <div>
                    <span>会话</span>
                    <strong>{{ authStore.token ? '已连接' : '未登录' }}</strong>
                  </div>
                </div>
                <div class="profile-avatar-picker" data-test="profile-avatar-picker">
                  <span>头像形象</span>
                  <div>
                    <button
                      v-for="avatar in builtInUserAvatars"
                      :key="avatar.id"
                      type="button"
                      :class="{ active: avatar.id === selectedUserAvatar.id }"
                      :title="avatar.name"
                      @click="selectUserAvatar(avatar.id)"
                    >
                      <img :src="avatar.src" :alt="avatar.name" />
                    </button>
                  </div>
                </div>
                <div class="profile-panel-actions">
                  <a-button block @click="navigateTo('/dashboard')">
                    <home-outlined />
                    返回首页
                  </a-button>
                  <a-button block @click="navigateTo('/personas')">
                    <team-outlined />
                    智能体工坊
                  </a-button>
                  <a-button block danger @click="handleLogout">
                    <logout-outlined />
                    退出登录
                  </a-button>
                </div>
              </div>
            </template>
            <button
              type="button"
              class="profile-button"
              :class="{ collapsed }"
              data-test="sidebar-profile"
            >
              <a-avatar :size="collapsed ? 34 : 42" class="profile-avatar">
                <img v-if="userAvatarSrc" :src="userAvatarSrc" :alt="displayName" />
                <template v-else>{{ userInitial }}</template>
              </a-avatar>
              <span v-if="!collapsed" class="profile-meta">
                <strong>{{ displayName }}</strong>
                <em>ID {{ userIdLabel }}</em>
              </span>
              <right-outlined v-if="!collapsed" class="profile-arrow" />
            </button>
          </a-popover>
        </div>
      </div>
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
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { builtInUserAvatars, resolveBuiltInUserAvatar, USER_AVATAR_STORAGE_KEY } from '@/utils/avatar'
import {
  DashboardOutlined,
  TeamOutlined,
  AppstoreOutlined,
  ToolOutlined,
  ClockCircleOutlined,
  LogoutOutlined,
  RightOutlined,
  HomeOutlined
} from '@ant-design/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const collapsed = ref(false)
const profileOpen = ref(false)
const selectedUserAvatarId = ref(localStorage.getItem(USER_AVATAR_STORAGE_KEY) || '')

const displayName = computed(() => authStore.user?.username || '未登录用户')
const userInitial = computed(() => displayName.value[0]?.toUpperCase() || 'U')
const userIdLabel = computed(() => authStore.user?.id ?? '-')
const selectedUserAvatar = computed(() => {
  return resolveBuiltInUserAvatar(authStore.user, selectedUserAvatarId.value)
})
const userAvatarSrc = computed(() => selectedUserAvatar.value.src)
const roleLabel = computed(() => {
  switch (authStore.user?.role) {
    case 'admin': return '管理员'
    case 'god': return 'God 模式'
    case 'user': return '普通用户'
    default: return '访客'
  }
})

const handleLogout = async () => {
  profileOpen.value = false
  await authStore.logout()
}

const selectUserAvatar = (avatarId: string) => {
  selectedUserAvatarId.value = avatarId
  localStorage.setItem(USER_AVATAR_STORAGE_KEY, avatarId)
}

const navigateTo = (path: string) => {
    profileOpen.value = false
    router.push(path)
}

const selectedKeys = computed(() => {
  if (route.path === '/' || route.path.startsWith('/dashboard')) return ['dashboard']
  if (route.path.startsWith('/personas')) return ['personas']
  if (route.path.startsWith('/forums')) return ['dashboard']
  if (route.path.startsWith('/assistants/skills')) return ['skills']
  if (route.path.startsWith('/assistants')) return ['assistants']
  if (route.path.startsWith('/time-gate')) return ['time-gate']
  return []
})

// 监听登录状�?
watch(() => authStore.token, (token) => {
  if (!token) {
    router.push('/auth/login')
  }
}, { immediate: true })
</script>

<style scoped>
.logo {
  height: 72px;
  margin: 18px 14px 20px;
  background: #1a1d1e;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  border-radius: 18px;
  overflow: hidden;
  white-space: nowrap;
  box-shadow: 0 12px 28px rgba(20, 23, 21, 0.18);
}

.logo.collapsed {
  height: 58px;
  margin: 14px 8px 16px;
  gap: 0;
  border-radius: 16px;
}

.logo-icon {
  width: 52px;
  height: 52px;
  object-fit: contain;
  border-radius: 12px;
  flex-shrink: 0;
}

.logo.collapsed .logo-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
}

.logo-text {
  font-size: 26px;
  font-weight: 850;
  color: white;
  line-height: 1;
  letter-spacing: 0;
}

.logo.collapsed .logo-text {
  display: none;
}

.sider-layout {
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
  z-index: 10;
  height: 100vh;
  overflow: hidden;
  background: #ffffff;
  border-right: 1px solid #f0f0f0;
}

.sider-layout :deep(.ant-layout-sider-children) {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sider-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 16px;
}

.nav-menu {
  border: none;
  padding: 8px;
  flex: 1;
  overflow-y: auto;
}

.nav-menu :deep(.ant-menu-item) {
  margin: 4px 0;
  border-radius: 10px;
  transition: all 0.3s ease;
}

.nav-menu :deep(.ant-menu-item-selected) {
  background: #171a18 !important;
  color: #bee83f !important;
  box-shadow: 0 8px 22px rgba(23, 26, 24, 0.18);
}

.nav-menu :deep(.ant-menu-item-selected .anticon),
.nav-menu :deep(.ant-menu-item-selected span) {
  color: #bee83f !important;
}

.nav-menu :deep(.ant-menu-item:not(.ant-menu-item-selected):hover) {
  background: #ebf7ee;
  color: #3bb36b;
}

.nav-icon {
  font-size: 18px;
}

.menu-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent 0%, #e8e8e8 50%, transparent 100%);
  margin: 16px 8px;
}

.profile-dock {
  flex-shrink: 0;
  padding: 12px;
  border-top: 1px solid #edf2ee;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.65), #ffffff);
}

.profile-button {
  width: 100%;
  min-height: 58px;
  border: 1px solid #e0ece4;
  background: #f8fbf8;
  border-radius: 14px;
  padding: 8px;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.22s ease;
}

.profile-button:hover {
  border-color: #3bb36b;
  background: #eef8f0;
  box-shadow: 0 12px 24px rgba(59, 179, 107, 0.12);
}

.profile-button.collapsed {
  min-height: 48px;
  display: flex;
  justify-content: center;
  padding: 6px;
}

.profile-avatar,
.profile-panel-avatar {
  background: #3bb36b;
  color: white;
  font-weight: 750;
  box-shadow: 0 8px 16px rgba(59, 179, 107, 0.24);
}

.profile-avatar :deep(img),
.profile-panel-avatar :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.profile-meta {
  min-width: 0;
  text-align: left;
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.profile-meta strong {
  color: #141816;
  font-size: 13px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.profile-meta em {
  color: #738078;
  font-size: 11px;
  font-style: normal;
  margin-top: 4px;
}

.profile-arrow {
  color: #8aa092;
  font-size: 12px;
}

.profile-panel {
  width: 268px;
}

.profile-panel-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid #edf2ee;
}

.profile-panel-name {
  color: #141816;
  font-size: 16px;
  font-weight: 750;
  line-height: 1.2;
  word-break: break-all;
}

.profile-panel-id {
  color: #738078;
  font-size: 12px;
  margin-top: 4px;
}

.profile-panel-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin: 14px 0;
}

.profile-panel-grid div {
  min-height: 62px;
  border: 1px solid #e6eee8;
  border-radius: 12px;
  background: #f8fbf8;
  padding: 10px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.profile-panel-grid span {
  color: #7b887f;
  font-size: 12px;
}

.profile-panel-grid strong {
  color: #151917;
  font-size: 14px;
}

.profile-avatar-picker {
  border: 1px solid #e6eee8;
  border-radius: 12px;
  background: #f8fbf8;
  padding: 10px;
  margin-bottom: 12px;
}

.profile-avatar-picker > span {
  display: block;
  color: #7b887f;
  font-size: 12px;
  margin-bottom: 8px;
}

.profile-avatar-picker > div {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.profile-avatar-picker button {
  width: 42px;
  height: 42px;
  border: 1px solid transparent;
  border-radius: 12px;
  padding: 2px;
  background: transparent;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.profile-avatar-picker button:hover,
.profile-avatar-picker button.active {
  transform: translateY(-1px);
  border-color: #3bb36b;
  box-shadow: 0 8px 16px rgba(59, 179, 107, 0.16);
}

.profile-avatar-picker img {
  width: 100%;
  height: 100%;
  border-radius: 10px;
  object-fit: cover;
  display: block;
}

.profile-panel-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.profile-panel-actions :deep(.ant-btn) {
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.site-layout {
  min-height: 100vh;
  background: #f2f7f3;
  position: relative;
}

.site-layout::before {
  content: '';
  position: fixed;
  top: -15%;
  right: -8%;
  width: 650px;
  height: 650px;
  background: radial-gradient(circle, rgba(59, 179, 107, 0.07) 0%, transparent 65%);
  pointer-events: none;
  z-index: 0;
}

.site-layout::after {
  content: '';
  position: fixed;
  bottom: -10%;
  left: 5%;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(59, 179, 107, 0.05) 0%, transparent 65%);
  pointer-events: none;
  z-index: 0;
}

.layout-content {
  margin: 0;
  padding: 0;
  min-height: 100vh;
  overflow-y: auto;
  position: relative;
  z-index: 1;
}

.content-wrapper {
  padding: 0;
  background: transparent;
  min-height: 100vh;
}
</style>
