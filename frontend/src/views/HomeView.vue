<template>
  <div class="dashboard-page">
    <section class="dashboard-grid fade-in-up" style="animation-delay: 0.15s;">
      <div class="left-stack">
        <div class="top-row">
          <div class="activity-panel insight-panel">
            <div class="panel-heading">
              <span class="panel-kicker">ACTIVITY</span>
              <h3>7日活跃</h3>
            </div>
            <div class="activity-strip">
              <button
                v-for="day in activityDays"
                :key="day.key"
                class="activity-day"
                :class="{ active: selectedDayKey === day.key }"
                :style="{ '--height': `${Math.max(12, day.intensity * 100)}%` }"
                @click="selectedDayKey = selectedDayKey === day.key ? null : day.key"
              >
                <span class="activity-bar"></span>
                <span class="activity-count">{{ day.count }}</span>
                <span class="activity-label">{{ day.label }}</span>
              </button>
            </div>
            <div class="activity-caption">
              <span>{{ selectedDayLabel }}</span>
              <button v-if="selectedDayKey" @click="selectedDayKey = null">清除筛选</button>
            </div>
          </div>

          <a-card :bordered="false" class="dashboard-card idea-card launch-panel">
            <template #title>
              <div class="card-title-section">
                <span class="card-title-icon">✦</span>
                <span class="card-title-text">议题发射台</span>
              </div>
            </template>
            <div class="idea-console">
              <p class="idea-topic">{{ featuredPrompt }}</p>
              <div class="idea-actions">
                <a-button type="primary" @click="startPrompt(featuredPrompt)" class="idea-launch-btn">
                  <plus-outlined />
                  立刻发起
                </a-button>
                <a-button @click="shufflePrompt" class="idea-shuffle-btn">
                  <reload-outlined />
                </a-button>
              </div>
              <div class="idea-chips">
                <button
                  v-for="prompt in promptIdeas.slice(0, 6)"
                  :key="prompt"
                  @click="startPrompt(prompt)"
                >
                  {{ prompt }}
                </button>
              </div>
            </div>
          </a-card>
        </div>

        <a-card :bordered="false" class="dashboard-card main-card forum-panel">
          <template #title>
            <div class="card-title-section">
              <span class="card-title-icon">📋</span>
              <span class="card-title-text">圆桌论坛</span>
            </div>
          </template>
          <template #extra>
            <a-button type="primary" @click="showCreateModal" class="card-create-btn">
              <plus-outlined />
              发起新论坛
            </a-button>
          </template>
          <div v-if="forumStore.loading && forumStore.forums.length === 0" class="loading-container">
            <a-spin size="large" />
            <p class="loading-text">加载中...</p>
          </div>
          <div v-else-if="forumStore.forums.length === 0" class="empty-container">
            <div class="empty-icon">🎯</div>
            <p class="empty-text">暂无活跃论坛</p>
            <a-button type="primary" @click="showCreateModal" class="empty-btn">
              发起第一个论坛
            </a-button>
          </div>
          <div v-else class="forum-list-container">
            <div
              v-for="item in filteredForums"
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
              <div class="forum-actions" @click.stop>
                <a-popconfirm
                  title="确定删除该论坛吗？"
                  ok-text="确定"
                  cancel-text="取消"
                  @confirm="handleDelete(item.id)"
                >
                  <a-button type="text" danger size="small" class="forum-delete-btn">
                    <delete-outlined />
                  </a-button>
                </a-popconfirm>
                <div class="forum-arrow">→</div>
              </div>
            </div>
            <div v-if="filteredForums.length === 0" class="filtered-empty">
              当前筛选下暂无论坛
            </div>
          </div>
        </a-card>
      </div>

      <div class="network-panel insight-panel network-rail">
        <div class="panel-heading">
          <div>
            <span class="panel-kicker">AGENTS</span>
            <h3>智能体星图</h3>
          </div>
          <a-button type="primary" class="persona-create-btn" @click="$router.push('/personas')">
            <plus-outlined />
            新建智能体
          </a-button>
        </div>
        <svg class="persona-map" viewBox="0 0 100 100" role="img" aria-label="智能体参与关系图">
          <defs>
            <clipPath v-for="node in personaNodes" :id="`persona-clip-${node.id}`" :key="`clip-${node.id}`">
              <circle :cx="node.x" :cy="node.y" :r="node.radius - 0.4" />
            </clipPath>
          </defs>
          <line
            v-for="node in personaNodes"
            :key="`line-${node.id}`"
            x1="50"
            y1="50"
            :x2="node.x"
            :y2="node.y"
            class="persona-link"
            :class="{ active: selectedPersonaId === node.id }"
          />
          <circle cx="50" cy="50" r="9" class="persona-hub" />
          <text x="50" y="52" text-anchor="middle" class="hub-label">Z</text>
          <g
            v-for="node in personaNodes"
            :key="node.id"
            class="persona-node"
            :class="{ active: selectedPersonaId === node.id }"
            @click="selectedPersonaId = selectedPersonaId === node.id ? null : node.id"
          >
            <circle :cx="node.x" :cy="node.y" :r="node.radius" />
            <image
              v-if="node.avatar"
              :href="node.avatar"
              :x="node.x - node.radius"
              :y="node.y - node.radius"
              :width="node.radius * 2"
              :height="node.radius * 2"
              :clip-path="`url(#persona-clip-${node.id})`"
              preserveAspectRatio="xMidYMid slice"
            />
            <text v-else :x="node.x" :y="node.y + 1.8" text-anchor="middle">{{ node.initial }}</text>
          </g>
        </svg>
        <div class="persona-focus">
          <span>{{ selectedPersonaName }}</span>
          <strong>{{ selectedPersonaForums.length }}</strong>
        </div>
      </div>
    </section>

    <a-modal
      v-model:open="createModalVisible"
      title="发起新讨论"
      :confirmLoading="submitting"
      width="560px"
      :footer="null"
      class="create-modal"
    >
      <div class="modal-content">
        <a-form layout="vertical" :model="formState" class="create-form">
          <a-form-item
            label="讨论主题"
            name="topic"
            :rules="[{ required: true, message: '请输入讨论主题' }]"
          >
            <a-input
              v-model:value="formState.topic"
              placeholder="例如：人工智能对未来就业的影响"
              size="large"
              class="form-input"
            />
          </a-form-item>

          <a-form-item
            label="邀请参与者"
            name="participant_ids"
            :rules="[{ required: true, message: '请至少选择一位智能体' }]"
          >
            <a-select
              v-model:value="formState.participant_ids"
              mode="multiple"
              placeholder="选择参与讨论的智能体"
              :options="personaOptions"
              :loading="personaStore.loading"
              size="large"
              style="width: 100%"
              class="form-select"
            >
              <template #option="{ label, avatar }">
                <div class="select-option">
                  <span class="option-avatar">
                    <img v-if="getPersonaAvatarSrc(avatar)" :src="getPersonaAvatarSrc(avatar)" :alt="label" />
                    <template v-else>{{ getAvatarInitial(label, '智') }}</template>
                  </span>
                  <span>{{ label }}</span>
                </div>
              </template>
            </a-select>
            <div class="form-hint">
              💡 提示：先在智能体工坊创建智能体，再邀请他们加入圆桌讨论。
            </div>
          </a-form-item>

          <a-form-item label="论坛时长 (分钟)" name="duration">
            <a-input-number
              v-model:value="formState.duration"
              :min="5"
              :max="15"
              size="large"
              class="form-input-number"
            />
          </a-form-item>

          <div class="modal-actions">
            <a-button size="large" @click="createModalVisible = false" class="cancel-btn">
              取消
            </a-button>
            <a-button type="primary" size="large" @click="handleCreateForum" :loading="submitting" class="confirm-btn">
              发起讨论
            </a-button>
          </div>
        </a-form>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed, reactive, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { message } from 'ant-design-vue'
import { ClockCircleOutlined, PlusOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { getAvatarInitial, isImageAvatar } from '@/utils/avatar'

const authStore = useAuthStore()
const forumStore = useForumStore()
const personaStore = usePersonaStore()
const createModalVisible = ref(false)
const submitting = ref(false)
const selectedDayKey = ref<string | null>(null)
const selectedPersonaId = ref<number | null>(null)
const selectedPromptIndex = ref(0)

const formState = reactive({
  topic: '',
  participant_ids: [] as number[],
  duration: 5
})

const personaOptions = computed(() => {
  return personaStore.personas.map(p => ({
    label: p.name,
    value: p.id,
    avatar: p.avatar
  }))
})

const getPersonaAvatarSrc = (avatar?: string) => {
  return isImageAvatar(avatar) ? avatar : ''
}

const dateKey = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const forumDateKey = (dateString: string) => {
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return ''
  return dateKey(date)
}

const activityDays = computed(() => {
  const today = new Date()
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today)
    date.setDate(today.getDate() - (6 - index))
    return {
      key: dateKey(date),
      label: date.toLocaleDateString('zh-CN', { weekday: 'short' }).replace('周', ''),
      count: 0,
      intensity: 0
    }
  })

  forumStore.forums.forEach(forum => {
    const key = forumDateKey(forum.start_time)
    const day = days.find(item => item.key === key)
    if (day) day.count += 1
  })

  const maxCount = Math.max(...days.map(day => day.count), 1)
  return days.map(day => ({
    ...day,
    intensity: day.count / maxCount
  }))
})

const selectedDayLabel = computed(() => {
  if (!selectedDayKey.value) return '点击任意一天筛选论坛'
  const day = activityDays.value.find(item => item.key === selectedDayKey.value)
  return day ? `${day.key} 创建 ${day.count} 个论坛` : '点击任意一天筛选论坛'
})

const filteredForums = computed(() => {
  return forumStore.forums.filter(forum => {
    const matchesDay = !selectedDayKey.value || forumDateKey(forum.start_time) === selectedDayKey.value
    return matchesDay
  })
})

const personaNodes = computed(() => {
  const personas = personaStore.personas.slice(0, 8)
  const total = Math.max(personas.length, 1)
  return personas.map((persona, index) => {
    const angle = (Math.PI * 2 * index) / total - Math.PI / 2
    const participation = forumStore.forums.filter(forum => {
      return forum.participants?.some((participant: any) => participant.persona_id === persona.id || participant.id === persona.id)
    }).length
    return {
      id: persona.id,
      name: persona.name,
      initial: getAvatarInitial(persona.name, '智'),
      avatar: getPersonaAvatarSrc(persona.avatar),
      x: 50 + Math.cos(angle) * 34,
      y: 50 + Math.sin(angle) * 34,
      radius: Math.min(8, 4.5 + participation)
    }
  })
})

const selectedPersonaName = computed(() => {
  if (!selectedPersonaId.value) return '点击节点查看参与'
  return personaStore.personas.find(persona => persona.id === selectedPersonaId.value)?.name || '未知智能体'
})

const selectedPersonaForums = computed(() => {
  if (!selectedPersonaId.value) return []
  return forumStore.forums.filter(forum => {
    return forum.participants?.some((participant: any) => participant.persona_id === selectedPersonaId.value || participant.id === selectedPersonaId.value)
  })
})

const promptIdeas = computed(() => [
  '让智能体辩论一个产品决策的正反两面',
  '用圆桌方式拆解下一个版本的风险',
  '请三位智能体模拟投资人评审这个想法',
  '围绕用户留存做一次多角色复盘',
  '把一个模糊需求拆成三条可执行路线',
  '模拟一次发布前的红队评审',
  '让不同角色评估当前方案的机会成本',
  '用反方视角挑战这个商业假设',
  '为下一次会议生成议程和分工',
  '请智能体提出一个更大胆的替代方案',
  `基于已有 ${forumStore.forums.length} 个论坛总结下一步行动`,
  `让 ${personaStore.personas.length || 3} 位智能体设计一个新功能`
])

const featuredPrompt = computed(() => promptIdeas.value[selectedPromptIndex.value % promptIdeas.value.length])

const getAvatarGradient = (text: string) => {
  const colors = [
    '#3bb36b',
    '#2fa15c',
    '#3bb36b',
    '#2fa15c',
    '#3bb36b',
    '#2fa15c'
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

const resetCreateForm = () => {
  formState.topic = ''
  formState.participant_ids = []
  formState.duration = 5
}

const showCreateModal = (initialTopic: string | MouseEvent = '') => {
  resetCreateForm()
  formState.topic = typeof initialTopic === 'string' ? initialTopic : ''
  createModalVisible.value = true
  personaStore.fetchPersonas(authStore.user?.id)
}

const startPrompt = (topic: string) => {
  showCreateModal(topic)
}

const shufflePrompt = () => {
  selectedPromptIndex.value = (selectedPromptIndex.value + 1) % promptIdeas.value.length
}

const handleCreateForum = async () => {
  if (!formState.topic.trim() || formState.participant_ids.length === 0) {
    message.warning('请填写完整信息')
    return
  }

  submitting.value = true
  try {
    await forumStore.createForum(formState.topic.trim(), formState.participant_ids, formState.duration)
    createModalVisible.value = false
    message.success('讨论发起成功！')
  } catch (e: unknown) {
    if (e instanceof Error) {
      message.error(e.message || '创建失败')
    } else {
      message.error('创建失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await forumStore.deleteForum(id)
    message.success('删除成功')
  } catch (e: unknown) {
    if (e instanceof Error) {
      message.error(e.message || '删除失败')
    } else {
      message.error('删除失败')
    }
  }
}

onMounted(() => {
  forumStore.fetchForums()
  personaStore.fetchPersonas(authStore.user?.id)
})
</script>

<style scoped>
.dashboard-page {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: 22px 28px 28px;
  min-height: 100vh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.dashboard-grid {
  flex: 1;
  min-height: calc(100vh - 50px);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 360px);
  gap: 20px;
}

.left-stack {
  min-width: 0;
  display: grid;
  grid-template-rows: 300px minmax(0, 1fr);
  gap: 20px;
}

.top-row {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(340px, 0.78fr) minmax(420px, 1.22fr);
  gap: 20px;
}

.insight-panel {
  height: 100%;
  min-height: 0;
  background: #ffffff;
  border: 1px solid #e5ece7;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 12px 30px rgba(28, 31, 34, 0.07);
  position: relative;
  overflow: hidden;
}

.insight-panel::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(59, 179, 107, 0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59, 179, 107, 0.07) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.7), transparent 72%);
  pointer-events: none;
}

.panel-heading {
  position: relative;
  z-index: 1;
  margin-bottom: 8px;
}

.panel-kicker {
  display: block;
  color: #738078;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0;
  margin-bottom: 2px;
}

.panel-heading h3 {
  margin: 0;
  color: #141816;
  font-size: 17px;
  font-weight: 750;
  letter-spacing: 0;
}

.activity-panel {
  display: flex;
  flex-direction: column;
}

.activity-strip {
  flex: 1;
  min-height: 168px;
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  align-items: end;
  gap: 6px;
  position: relative;
  z-index: 1;
}

.activity-day {
  height: 168px;
  border: 1px solid #e4ebe6;
  background: #fbfcfb;
  border-radius: 10px;
  padding: 8px 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 5px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.activity-day:hover,
.activity-day.active {
  border-color: #3bb36b;
  background: #eff8f1;
  transform: translateY(-3px);
}

.activity-bar {
  width: 100%;
  height: var(--height);
  min-height: 12px;
  border-radius: 8px;
  background: linear-gradient(180deg, #bee83f 0%, #3bb36b 100%);
  box-shadow: inset 0 -10px 16px rgba(20, 24, 22, 0.12);
}

.activity-count {
  color: #111513;
  font-size: 13px;
  font-weight: 700;
}

.activity-label {
  color: #738078;
  font-size: 11px;
}

.activity-caption {
  min-height: 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #637069;
  font-size: 12px;
  position: relative;
  z-index: 1;
}

.activity-caption button {
  border: none;
  background: transparent;
  color: #2fa15c;
  cursor: pointer;
  padding: 0;
}

.network-panel {
  display: flex;
  flex-direction: column;
}

.network-rail {
  grid-column: 2;
  grid-row: 1;
}

.network-rail .panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.persona-map {
  width: 100%;
  min-height: 360px;
  flex: 1;
  position: relative;
  z-index: 1;
}

.persona-link {
  stroke: #d8e3dc;
  stroke-width: 0.8;
  transition: stroke 0.2s ease, stroke-width 0.2s ease;
}

.persona-link.active {
  stroke: #3bb36b;
  stroke-width: 1.6;
}

.persona-hub {
  fill: #151917;
}

.hub-label {
  fill: #bee83f;
  font-size: 8px;
  font-weight: 800;
}

.persona-node {
  cursor: pointer;
}

.persona-node circle {
  fill: #ffffff;
  stroke: #3bb36b;
  stroke-width: 1.8;
  filter: drop-shadow(0 5px 7px rgba(31, 36, 33, 0.16));
  transition: fill 0.2s ease, transform 0.2s ease;
}

.persona-node text {
  fill: #151917;
  font-size: 4px;
  font-weight: 800;
  pointer-events: none;
}

.persona-node image {
  pointer-events: none;
}

.persona-node:hover circle,
.persona-node.active circle {
  fill: #bee83f;
}

.persona-focus {
  min-height: 30px;
  border: 1px solid #e4ebe6;
  background: #f8faf8;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  color: #637069;
  font-size: 12px;
  position: relative;
  z-index: 1;
}

.persona-focus strong {
  color: #151917;
}

.dashboard-card {
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
  width: 100%;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dashboard-card :deep(.ant-card-body) {
  flex: 1;
  min-height: 0;
}

.main-card {
  min-height: 100%;
}

.forum-panel {
  min-height: 0;
}

.main-card :deep(.ant-card-body) {
  display: flex;
  flex-direction: column;
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
  color: #1a1d1e;
}

.card-create-btn {
  height: 42px;
  padding: 0 18px;
  background: #bee83f;
  border: none;
  border-radius: 999px;
  color: #151917;
  font-size: 15px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 12px 24px rgba(190, 232, 63, 0.28);
}

.card-create-btn:hover {
  background: #d5f870;
  color: #151917;
  transform: translateY(-1px);
}

.loading-container,
.empty-container {
  flex: 1;
  min-height: 320px;
  text-align: center;
  padding: 48px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.loading-text {
  margin-top: 12px;
  color: #787f84;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-text {
  color: #787f84;
  margin-bottom: 20px;
}

.empty-btn {
  background: #bee83f;
  border: none;
  border-radius: 999px;
  height: 46px;
  color: #151917;
  font-weight: 800;
  padding: 0 24px;
  box-shadow: 0 12px 24px rgba(190, 232, 63, 0.28);
}

.forum-list-container {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  align-content: start;
  gap: 12px;
  max-height: none;
  overflow-y: auto;
  padding-right: 4px;
}

.filtered-empty {
  padding: 32px 16px;
  border: 1px dashed #cbd8cf;
  border-radius: 12px;
  color: #738078;
  text-align: center;
  background: #fbfcfb;
}

.forum-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border-radius: 12px;
  background: #f8faf8;
  border: 1px solid transparent;
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 0;
}

.forum-item:hover {
  background: #eef5f0;
  border-color: #dbe8df;
  transform: translateY(-2px);
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
  color: #1a1d1e;
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
  color: #787f84;
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
  color: #3bb36b;
  transform: translateX(4px);
}

.forum-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.forum-delete-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.idea-card {
  background: #151917;
  color: #ffffff;
  min-height: 100%;
}

.launch-panel {
  height: 100%;
}

.idea-card :deep(.ant-card-head) {
  border-bottom-color: rgba(255, 255, 255, 0.12);
}

.idea-card .card-title-text,
.idea-card .card-title-icon {
  color: #bee83f;
}

.idea-console {
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.idea-topic {
  min-height: 58px;
  margin: 0;
  color: #f6fbf5;
  font-size: 20px;
  line-height: 1.42;
  font-weight: 650;
}

.idea-actions {
  display: grid;
  grid-template-columns: 1fr 48px;
  gap: 10px;
}

.idea-launch-btn {
  height: 52px;
  background: #bee83f;
  border: none;
  color: #151917;
  font-weight: 700;
  border-radius: 12px;
}

.idea-launch-btn:hover {
  background: #d5f870;
  color: #151917;
}

.idea-shuffle-btn {
  height: 52px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.06);
  color: #ffffff;
  border-radius: 12px;
}

.idea-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  align-content: flex-start;
  max-height: 76px;
  overflow: hidden;
}

.idea-chips button {
  border: 1px solid rgba(190, 232, 63, 0.32);
  background: rgba(190, 232, 63, 0.08);
  color: #eaf5d3;
  border-radius: 999px;
  padding: 5px 9px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.persona-create-btn {
  height: 42px;
  border: none;
  border-radius: 999px;
  background: #bee83f;
  color: #151917;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 850;
  padding: 0 18px;
  box-shadow: 0 14px 28px rgba(190, 232, 63, 0.32);
}

.persona-create-btn:hover {
  background: #d5f870;
  color: #151917;
  transform: translateY(-1px);
}

.idea-chips button:hover {
  background: rgba(190, 232, 63, 0.18);
  border-color: rgba(190, 232, 63, 0.6);
}

.create-modal :deep(.ant-modal-content) {
  border-radius: 20px;
  padding: 8px;
}

.create-modal :deep(.ant-modal-header) {
  border: none;
  padding: 20px 24px 8px;
}

.create-modal :deep(.ant-modal-title) {
  font-size: 20px;
  font-weight: 700;
  color: #1a1d1e;
}

.modal-content {
  padding: 8px 24px 16px;
}

.create-form {
  margin-bottom: 0;
}

.form-input,
.form-select,
.form-input-number {
  border-radius: 10px;
}

.form-input :deep(.ant-input),
.form-select :deep(.ant-select-selector),
.form-input-number :deep(.ant-input-number-input-wrap) {
  border-radius: 10px;
}

.form-hint {
  margin-top: 10px;
  color: #3bb36b;
  font-size: 13px;
  background: #ebf7ee;
  padding: 10px 14px;
  border-radius: 8px;
  line-height: 1.5;
}

.select-option {
  display: flex;
  align-items: center;
  gap: 10px;
}

.option-avatar {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #3bb36b;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  flex-shrink: 0;
}

.option-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 8px;
}

.cancel-btn {
  height: 44px;
  border-radius: 10px;
  padding: 0 24px;
  font-weight: 500;
  background: #eef5f0;
  border: none;
  color: #1a1d1e;
}

.confirm-btn {
  height: 44px;
  border-radius: 10px;
  padding: 0 28px;
  font-weight: 600;
  background: #3bb36b;
  border: none;
  box-shadow: 0 4px 12px rgba(59, 179, 107, 0.3);
}

@media (max-width: 768px) {
  .dashboard-page {
    padding: 14px 16px 18px;
    min-height: auto;
  }

  .dashboard-grid,
  .left-stack,
  .top-row {
    grid-template-columns: 1fr;
    grid-template-rows: auto;
    gap: 14px;
    min-height: auto;
  }

  .insight-panel {
    height: auto;
    min-height: 190px;
  }

  .network-rail {
    grid-column: auto;
    grid-row: auto;
  }

  .activity-strip {
    min-height: 104px;
    gap: 6px;
  }

  .activity-day {
    height: 104px;
    padding: 8px 4px;
  }

  .persona-map {
    min-height: 180px;
  }
  
  .forum-item {
    align-items: flex-start;
  }

  .forum-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 6px;
  }

  .forum-actions {
    gap: 4px;
  }

  .forum-list-container {
    grid-template-columns: 1fr;
    max-height: none;
    min-height: auto;
  }

  .modal-actions {
    flex-direction: column;
  }

  .cancel-btn,
  .confirm-btn {
    width: 100%;
  }
}

</style>
