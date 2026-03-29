<template>
  <div class="dashboard-page">
    <div class="welcome-section fade-in-up">
      <div class="welcome-content">
        <div class="avatar-section">
          <a-avatar size="large" class="user-avatar" style="background: linear-gradient(-225deg, #69EACB 0%, #EACCF8 48%, #6654F1 100%);">
            {{ authStore.user?.username?.[0]?.toUpperCase() }}
          </a-avatar>
          <div class="welcome-text">
            <h2 class="welcome-title">欢迎回来，{{ authStore.user?.username }}！</h2>
            <p class="welcome-subtitle">今天要和智能体们探讨什么有趣的话题呢？</p>
          </div>
        </div>
        <div class="greeting-emoji">👋</div>
      </div>
    </div>

    <a-row :gutter="[20, 20]" class="stats-row fade-in-up" style="animation-delay: 0.1s;">
      <a-col :xs="12" :sm="6">
        <div class="stat-card stat-card-1">
          <div class="stat-icon">💬</div>
          <div class="stat-content">
            <div class="stat-number">{{ forumStore.forums.length }}</div>
            <div class="stat-label">论坛总数</div>
          </div>
        </div>
      </a-col>
      <a-col :xs="12" :sm="6">
        <div class="stat-card stat-card-2">
          <div class="stat-icon">🤖</div>
          <div class="stat-content">
            <div class="stat-number">{{ personaStore.personas.length }}</div>
            <div class="stat-label">智能体</div>
          </div>
        </div>
      </a-col>
      <a-col :xs="12" :sm="6">
        <div class="stat-card stat-card-3">
          <div class="stat-icon">🔥</div>
          <div class="stat-content">
            <div class="stat-number">{{ activeForumsCount }}</div>
            <div class="stat-label">进行中</div>
          </div>
        </div>
      </a-col>
      <a-col :xs="12" :sm="6">
        <div class="stat-card stat-card-4">
          <div class="stat-icon">⭐</div>
          <div class="stat-content">
            <div class="stat-number">{{ today }}</div>
            <div class="stat-label">今日</div>
          </div>
        </div>
      </a-col>
    </a-row>

    <a-row :gutter="[24, 24]" class="content-row">
      <a-col :xs="24" :lg="16" class="fade-in-up" style="animation-delay: 0.2s;">
        <a-card :bordered="false" class="dashboard-card main-card">
          <template #title>
            <div class="card-title-section">
              <span class="card-title-icon">📋</span>
              <span class="card-title-text">最近活跃论坛</span>
            </div>
          </template>
          <template #extra><router-link to="/forums" class="view-all-link">查看全部 →</router-link></template>
          <div v-if="forumStore.loading" class="loading-container">
            <a-spin size="large" />
            <p class="loading-text">加载中...</p>
          </div>
          <div v-else-if="forumStore.forums.length === 0" class="empty-container">
            <div class="empty-icon">🎯</div>
            <p class="empty-text">暂无活跃论坛</p>
            <a-button type="primary" @click="$router.push('/forums')" class="empty-btn">
              发起第一个讨论
            </a-button>
          </div>
          <div v-else class="forum-list-container">
            <div
              v-for="item in forumStore.forums.slice(0, 5)"
              :key="item.id"
              class="forum-item"
              @click="$router.push(`/forums/${item.id}`)"
            >
              <div class="forum-avatar" :style="{ background: getAvatarGradient(item.topic) }">
                {{ item.topic[0] }}
              </div>
              <div class="forum-info">
                <div class="forum-topic">{{ item.topic }}</div>
                <div class="forum-meta">
                  <span class="forum-date">
                    <clock-circle-outlined /> {{ formatDate(item.start_time) }}
                  </span>
                  <a-tag :color="item.status === 'active' || item.status === 'running' ? 'processing' : 'default'" class="forum-tag">
                    {{ getStatusText(item.status) }}
                  </a-tag>
                </div>
              </div>
              <div class="forum-arrow">→</div>
            </div>
          </div>
        </a-card>
      </a-col>
      
      <a-col :xs="24" :lg="8" class="fade-in-up" style="animation-delay: 0.3s;">
        <div class="side-column">
          <a-card :bordered="false" class="dashboard-card actions-card">
            <template #title>
              <div class="card-title-section">
                <span class="card-title-icon">⚡</span>
                <span class="card-title-text">快捷操作</span>
              </div>
            </template>
            <div class="quick-actions">
              <a-button type="primary" block @click="$router.push('/personas')" class="action-btn action-btn-primary">
                <team-outlined class="btn-icon" />
                <span>创建新智能体</span>
              </a-button>
              <a-button block @click="$router.push('/forums')" class="action-btn action-btn-secondary">
                <comment-outlined class="btn-icon" />
                <span>发起新讨论</span>
              </a-button>
              <a-button block @click="authStore.logout()" class="action-btn action-btn-logout">
                <logout-outlined class="btn-icon" />
                <span>退出登录</span>
              </a-button>
            </div>
          </a-card>

          <a-card :bordered="false" class="dashboard-card personas-card">
            <template #title>
              <div class="card-title-section">
                <span class="card-title-icon">🎭</span>
                <span class="card-title-text">我的智能体</span>
              </div>
            </template>
            <template #extra><router-link to="/personas" class="view-all-link">管理 →</router-link></template>
            <div class="persona-mini-list">
              <div v-if="personaStore.loading" class="persona-loading">
                <a-spin size="small" />
              </div>
              <div v-else-if="personaStore.personas.length === 0" class="persona-empty">
                <span class="empty-emoji">🤖</span>
                <span>暂无智能体</span>
              </div>
              <template v-else>
                <div v-for="p in personaStore.personas.slice(0, 4)" :key="p.id" class="persona-item">
                  <a-avatar size="small" :style="{ background: getAvatarGradient(p.name) }">{{ p.name[0] }}</a-avatar>
                  <span class="persona-name">{{ p.name }}</span>
                </div>
              </template>
            </div>
          </a-card>
        </div>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { TeamOutlined, CommentOutlined, LogoutOutlined, ClockCircleOutlined } from '@ant-design/icons-vue'

const authStore = useAuthStore()
const forumStore = useForumStore()
const personaStore = usePersonaStore()

const today = computed(() => {
  const d = new Date()
  return d.getDate()
})

const activeForumsCount = computed(() => {
  return forumStore.forums.filter(f => f.status === 'active' || f.status === 'running').length
})

const getAvatarGradient = (text: string) => {
  const colors = [
    'linear-gradient(-225deg, #69EACB 0%, #EACCF8 48%, #6654F1 100%)',
    'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
    'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)'
  ]
  let hash = 0
  for (let i = 0; i < text.length; i++) {
    hash = text.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}

const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60))
  
  if (hours < 1) return '刚刚'
  if (hours < 24) return `${hours}小时前`
  if (hours < 48) return '昨天'
  return date.toLocaleDateString('zh-CN')
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'running':
    case 'active': return '进行中'
    case 'pending': return '未开始'
    case 'closed':
    case 'finished': return '已结束'
    default: return '未知'
  }
}

onMounted(() => {
  forumStore.fetchForums()
  personaStore.fetchPersonas(authStore.user?.id)
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px;
  min-height: 100vh;
}

.welcome-section {
  margin-bottom: 32px;
}

.welcome-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(-225deg, #69EACB 0%, #EACCF8 48%, #6654F1 100%);
  border-radius: 24px;
  padding: 32px;
  box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
}

.avatar-section {
  display: flex;
  align-items: center;
  gap: 20px;
}

.user-avatar {
  border: 4px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.welcome-text {
  color: white;
}

.welcome-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 6px;
  color: white;
}

.welcome-subtitle {
  font-size: 15px;
  margin: 0;
  color: rgba(255, 255, 255, 0.9);
}

.greeting-emoji {
  font-size: 48px;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
  cursor: pointer;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
}

.stat-card-1 {
  border-left: 4px solid #667eea;
}

.stat-card-2 {
  border-left: 4px solid #f093fb;
}

.stat-card-3 {
  border-left: 4px solid #4facfe;
}

.stat-card-4 {
  border-left: 4px solid #43e97b;
}

.stat-icon {
  font-size: 36px;
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  border-radius: 14px;
}

.stat-content {
  flex: 1;
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #888;
  font-weight: 500;
}

.content-row {
  margin-top: 8px;
}

.dashboard-card {
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  height: 100%;
  overflow: hidden;
}

.main-card {
  min-height: 450px;
}

.card-title-section {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title-icon {
  font-size: 20px;
}

.card-title-text {
  font-weight: 600;
  font-size: 16px;
  color: #1a1a2e;
}

.view-all-link {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
  font-size: 14px;
  transition: all 0.3s ease;
}

.view-all-link:hover {
  color: #764ba2;
}

.loading-container,
.empty-container {
  text-align: center;
  padding: 48px 24px;
}

.loading-text {
  margin-top: 12px;
  color: #888;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-text {
  color: #888;
  margin-bottom: 20px;
}

.empty-btn {
  background: linear-gradient(-225deg, #69EACB 0%, #EACCF8 48%, #6654F1 100%);
  border: none;
  border-radius: 10px;
  height: 42px;
  font-weight: 500;
}

.forum-list-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.forum-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border-radius: 12px;
  background: #f8f9fb;
  cursor: pointer;
  transition: all 0.3s ease;
}

.forum-item:hover {
  background: #f0f2f5;
  transform: translateX(4px);
}

.forum-avatar {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 600;
  color: white;
  flex-shrink: 0;
}

.forum-info {
  flex: 1;
  min-width: 0;
}

.forum-topic {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.forum-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.forum-date {
  font-size: 13px;
  color: #888;
  display: flex;
  align-items: center;
  gap: 4px;
}

.forum-tag {
  font-size: 12px;
}

.forum-arrow {
  font-size: 20px;
  color: #ccc;
  transition: all 0.3s ease;
}

.forum-item:hover .forum-arrow {
  color: #667eea;
  transform: translateX(4px);
}

.side-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-btn {
  height: 48px;
  font-size: 15px;
  font-weight: 500;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.3s ease;
  border: none;
}

.btn-icon {
  font-size: 18px;
}

.action-btn-primary {
  background: linear-gradient(-225deg, #69EACB 0%, #EACCF8 48%, #6654F1 100%);
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.action-btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.action-btn-secondary {
  background: #f0f2f5;
  color: #1a1a2e;
}

.action-btn-secondary:hover {
  background: #e4e7ed;
  color: #667eea;
}

.action-btn-logout {
  background: #fff1f0;
  color: #ff4d4f;
}

.action-btn-logout:hover {
  background: #ffccc7;
}

.persona-mini-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.persona-loading {
  text-align: center;
  padding: 20px 0;
}

.persona-empty {
  text-align: center;
  padding: 20px 0;
  color: #999;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.empty-emoji {
  font-size: 32px;
}

.persona-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 10px;
  background: #f8f9fb;
  transition: all 0.3s ease;
  cursor: pointer;
}

.persona-item:hover {
  background: #f0f2f5;
  transform: translateX(4px);
}

.persona-name {
  font-size: 14px;
  color: #1a1a2e;
  font-weight: 500;
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 16px;
  }
  
  .welcome-content {
    flex-direction: column;
    text-align: center;
    padding: 24px;
  }
  
  .avatar-section {
    flex-direction: column;
    gap: 12px;
  }
  
  .welcome-title {
    font-size: 22px;
  }
  
  .welcome-subtitle {
    font-size: 14px;
  }
  
  .greeting-emoji {
    margin-top: 12px;
  }
  
  .stat-card {
    padding: 16px;
  }
  
  .stat-icon {
    width: 48px;
    height: 48px;
    font-size: 28px;
  }
  
  .stat-number {
    font-size: 24px;
  }
}

</style>