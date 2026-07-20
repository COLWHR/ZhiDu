<template>
  <div class="duxin-page">
    <section class="duxin-hero page-header fade-in-up">
      <div class="header-content">
        <div class="header-icon">渡</div>
        <div class="header-title">
          <span class="title">先和智小渡说说你现在的状态</span>
          <span class="subtitle">
            不需要先选择复杂服务。你先把问题、心情和身体状态说出来，智小渡会先接住，再分配更合适的支持视角。
          </span>
        </div>
      </div>
      <div class="hero-status">
        <span class="status-label">当前流程</span>
        <strong>{{ flowStatus }}</strong>
      </div>
    </section>

    <a-alert
      v-if="riskBanner"
      class="risk-alert fade-in-up"
      show-icon
      :type="riskBanner.type"
      :message="riskBanner.title"
      :description="riskBanner.description"
    />

    <main class="duxin-flow fade-in-up">
      <section class="intake-card">
        <div class="step-row" aria-label="渡心流程">
          <div v-for="step in flowSteps" :key="step.title" class="flow-step" :class="{ active: step.active }">
            <span>{{ step.index }}</span>
            <div>
              <strong>{{ step.title }}</strong>
              <small>{{ step.description }}</small>
            </div>
          </div>
        </div>

        <div class="intake-head">
          <span class="section-kicker">第一句话最重要</span>
          <h2>把此刻真实的状态交给智小渡</h2>
          <p>可以很乱，可以很短。比如：发生了什么、你现在最强烈的情绪是什么、身体有没有紧绷或失眠。</p>
        </div>

        <div class="companion-panel" aria-label="陪伴方式选择">
          <div class="companion-heading">
            <span class="section-kicker">先按你的节奏来</span>
            <h3>你希望我现在怎么陪你？</h3>
          </div>
          <div class="companion-options">
            <button
              v-for="choice in companionChoices"
              :key="choice.key"
              type="button"
              class="companion-option"
              :class="{ active: activeCompanionKey === choice.key }"
              @click="applyCompanionChoice(choice)"
            >
              <strong>{{ choice.label }}</strong>
              <span>{{ choice.description }}</span>
            </button>
          </div>
        </div>

        <div class="preset-list" aria-label="状态开头">
          <button
            v-for="preset in intakePresets"
            :key="preset.label"
            type="button"
            class="preset-chip"
            @click="applyPreset(preset)"
          >
            {{ preset.label }}
          </button>
        </div>

        <a-textarea
          ref="composerRef"
          v-model:value="draft"
          class="intake-input"
          :rows="6"
          :maxlength="4000"
          :disabled="store.streaming"
          placeholder="比如：我最近因为工作和关系都很焦虑，晚上睡不好，今天特别想哭，但又不知道该从哪里说起。"
          @keydown.enter="handleComposerEnter"
        />

        <div class="intake-actions">
          <div class="composer-state">
            <span class="state-dot" :class="{ active: store.streaming || !!store.composerStatus }"></span>
            <span>{{ composerHint }}</span>
          </div>
          <div class="action-buttons">
            <a-button v-if="hasConversation" @click="startNewConversation">
              重新开始
            </a-button>
            <a-button
              type="primary"
              size="large"
              class="send-button"
              :loading="store.streaming"
              :disabled="!draft.trim()"
              @click="handleSend"
            >
              <send-outlined />
              交给智小渡
            </a-button>
          </div>
        </div>
      </section>

      <aside class="assignment-card" :class="{ ready: !!assignedCounselor }">
        <div class="assignment-top">
          <span class="section-kicker">咨询师分配</span>
          <a-tag :color="modeTagColor(activeMode)">{{ modeLabel(activeMode) }}</a-tag>
        </div>

        <template v-if="assignedCounselor">
          <div class="counselor-avatar">
            <img
              v-if="getCounselorAvatarSrc(assignedCounselor)"
              :src="getCounselorAvatarSrc(assignedCounselor)"
              :alt="assignedCounselor.name"
            />
            <template v-else>{{ getAvatarInitial(assignedCounselor.name, '渡') }}</template>
          </div>
          <h2>智小渡建议先见 {{ assignedCounselor.name }}</h2>
          <p class="assignment-reason">{{ store.teamPlan?.handoff_reason }}</p>
          <div class="counselor-detail">
            <span>关注点</span>
            <strong>{{ assignedCounselor.focus }}</strong>
          </div>
          <div class="counselor-detail">
            <span>回应风格</span>
            <strong>{{ assignedCounselor.style }}</strong>
          </div>
          <div class="team-line">
            <span v-for="member in visibleTeamMembers" :key="member.key">{{ member.name }}</span>
          </div>
        </template>

        <template v-else>
          <div class="waiting-mark">
            <user-switch-outlined />
          </div>
          <h2>先不用选咨询师</h2>
          <p>
            智小渡会根据你发来的问题、情绪强度和安全信号判断。你说完第一段后，这里会显示被分配的咨询师。
          </p>
        </template>
      </aside>
    </main>

    <section class="conversation-card fade-in-up">
      <div class="conversation-head">
        <div>
          <span class="section-kicker">继续对话</span>
          <h2>{{ store.currentSessionTitle }}</h2>
        </div>
        <div class="conversation-tools">
          <a-button :loading="store.loading" @click="handleRefresh">
            <reload-outlined />
            刷新
          </a-button>
          <a-button :disabled="!store.currentSession" @click="handleArchiveCurrentSession">
            <inbox-outlined />
            收起
          </a-button>
        </div>
      </div>

      <div ref="messagesRef" class="messages">
        <div v-if="!hasConversation" class="empty-conversation">
          <team-outlined />
          <h3>智小渡还在等你的第一句话</h3>
          <p>这部分会保留你和智小渡、咨询师的对话。先从上面的输入框开始。</p>
        </div>

        <div
          v-for="item in store.messages"
          v-else
          :key="item.clientId || item.id"
          class="message-row"
          :class="item.role"
        >
          <a-avatar class="message-avatar" :style="messageAvatarStyle(item.role)">
            <img
              v-if="getMessageAvatarSrc(item)"
              :src="getMessageAvatarSrc(item)"
              :alt="speakerName(item)"
            />
            <template v-else>{{ item.role === 'user' ? userInitial : assistantInitial(item) }}</template>
          </a-avatar>
          <div class="message-body">
            <div class="message-meta">
              <strong>{{ speakerName(item) }}</strong>
              <span>{{ formatTime(item.created_at) }}</span>
            </div>
            <div class="message-bubble" :class="item.role">
              <div v-html="renderMarkdown(item.content)"></div>
            </div>
          </div>
        </div>

        <div v-if="store.streaming" class="message-row assistant">
          <a-avatar class="message-avatar" :style="assistantAvatarStyle">
            <img
              v-if="streamingAssistantAvatarSrc"
              :src="streamingAssistantAvatarSrc"
              :alt="assignedCounselor?.name || '智小渡'"
            />
            <template v-else>渡</template>
          </a-avatar>
          <div class="message-body">
            <div class="message-meta">
              <strong>{{ assignedCounselor?.name || '智小渡' }}</strong>
              <span>正在整理</span>
            </div>
            <div class="message-bubble assistant typing">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section v-if="recentSessions.length" class="history-strip fade-in-up">
      <div class="history-title">
        <span class="section-kicker">最近记录</span>
        <strong>想接着聊时，可以回到之前的会话</strong>
      </div>
      <button
        v-for="session in recentSessions"
        :key="session.id"
        class="history-item"
        :class="{ active: store.currentSession?.id === session.id }"
        type="button"
        @click="handleOpenSession(session.id)"
      >
        <span>{{ session.title }}</span>
        <small>{{ modeLabel(session.mode) }} · {{ formatTime(session.updated_at || session.created_at) }}</small>
      </button>
    </section>

    <section v-if="hasConversation" class="human-care-strip fade-in-up">
      <article class="heart-light-card">
        <span class="section-kicker">心灯卡</span>
        <p>{{ heartLightText }}</p>
        <small>这句话可以先放在这里。它不是评价，也不是任务，只是提醒你：此刻不用一个人硬撑。</small>
      </article>
      <article class="support-message-card">
        <div>
          <span class="section-kicker">现实求助短信</span>
          <p>{{ realWorldSupportMessage }}</p>
        </div>
        <button type="button" class="plain-tool-button" @click="copySupportMessage">
          复制短信
        </button>
      </article>
    </section>

    <section class="safety-note fade-in-up">
      <strong>安全边界</strong>
      <p>
        渡心不替代线下医疗或紧急救助。如果你担心自己或他人会受到伤害，请优先联系当地急救、危机热线，或让现实中可信任的人立刻陪在身边。
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import {
  InboxOutlined,
  ReloadOutlined,
  SendOutlined,
  TeamOutlined,
  UserSwitchOutlined
} from '@ant-design/icons-vue'
import { marked } from 'marked'
import { useAuthStore } from '@/stores/auth'
import { useDuxinStore } from '@/stores/duxin'
import type { DuxinMessage, DuxinMode, DuxinTeamMember } from '@/types/duxin'
import { generatePersonaAvatar, getAvatarInitial, resolveBuiltInUserAvatarSrc } from '@/utils/avatar'

marked.setOptions({ breaks: true, gfm: true })

type IntakePreset = {
  label: string
  prompt: string
  mode: DuxinMode
}

type CompanionChoice = {
  key: string
  label: string
  description: string
  prompt: string
  mode: DuxinMode
}

const authStore = useAuthStore()
const store = useDuxinStore()
const draft = ref('')
const draftMode = ref<DuxinMode>('support')
const activeCompanionKey = ref('stay')
const composerRef = ref()
const messagesRef = ref<HTMLElement | null>(null)

const companionChoices: CompanionChoice[] = [
  {
    key: 'stay',
    label: '只陪我一会儿',
    description: '先不分析，只把这一刻放慢。',
    mode: 'support',
    prompt: '我现在不太想被分析，只希望你先陪我一会儿。'
  },
  {
    key: 'clarify',
    label: '帮我理清楚',
    description: '把事情、感受和需要分开看。',
    mode: 'relationship',
    prompt: '我想请你帮我理清楚：发生了什么、我感受到什么、我真正需要什么。'
  },
  {
    key: 'action',
    label: '给我一个小行动',
    description: '不要太多建议，只要下一小步。',
    mode: 'growth',
    prompt: '我现在只需要一个今天能做到的小行动，不要太复杂。'
  },
  {
    key: 'danger',
    label: '我现在很危险',
    description: '先保护现实安全，再说别的。',
    mode: 'crisis',
    prompt: '我现在担心自己或他人可能不安全，请先帮我把注意力放在现实安全和求助上。'
  }
]

const intakePresets: IntakePreset[] = [
  {
    label: '我现在很焦虑',
    mode: 'support',
    prompt: '我现在很焦虑，脑子里有点乱，身体也紧绷。我想先说说发生了什么：'
  },
  {
    label: '关系让我很累',
    mode: 'relationship',
    prompt: '我最近被一段关系影响很大，心里很累，也有些委屈。我想先从这件事说起：'
  },
  {
    label: '我想整理下一步',
    mode: 'growth',
    prompt: '我现在卡住了，想把问题和下一步整理清楚。我的状态是：'
  },
  {
    label: '我需要先稳定',
    mode: 'crisis',
    prompt: '我现在情绪很强烈，需要先稳定下来。我此刻最难受的是：'
  }
]

const hasConversation = computed(() => !!store.currentSession || store.messages.length > 0)
const activeMode = computed(() => store.currentSession?.mode || store.teamPlan?.mode || draftMode.value)
const recentSessions = computed(() => store.sessions.slice(0, 4))
const latestAssistantMessage = computed(() => {
  return [...store.messages].reverse().find(item => item.role === 'assistant' && item.content.trim())
})

const assignedCounselor = computed<DuxinTeamMember | null>(() => {
  const members = store.teamPlan?.members || []
  return members.find(member => member.key !== 'zhidu') || store.teamPlan?.primary_agent || null
})

const visibleTeamMembers = computed(() => {
  const members = store.teamPlan?.members || []
  return members.filter(member => member.key !== 'zhidu').slice(0, 3)
})

const userInitial = computed(() => authStore.user?.username?.slice(0, 1).toUpperCase() || '你')

const userAvatarSrc = computed(() => resolveBuiltInUserAvatarSrc(authStore.user))

const flowStatus = computed(() => {
  if (store.streaming) return '智小渡正在判断'
  if (assignedCounselor.value) return `已分配：${assignedCounselor.value.name}`
  if (hasConversation.value) return '继续和智小渡聊'
  return '等待你的第一句话'
})

const flowSteps = computed(() => [
  { index: '01', title: '倾诉', description: '先说问题与状态', active: true },
  { index: '02', title: '判断', description: '识别心情和风险', active: store.streaming || !!store.teamPlan },
  { index: '03', title: '分配', description: '匹配合适咨询师', active: !!assignedCounselor.value }
])

const composerHint = computed(() => {
  if (store.composerStatus) return store.composerStatus
  if (store.streaming) return '智小渡正在听，并准备分配合适的咨询师'
  if (assignedCounselor.value) return `${assignedCounselor.value.name} 会接着这个方向陪你往下梳理`
  const choice = companionChoices.find(item => item.key === activeCompanionKey.value)
  if (choice) return choice.description
  return '可以只写一句，不需要组织成完整故事'
})

const heartLightText = computed(() => {
  if (store.riskLevel === 'L2' || store.riskLevel === 'L3') {
    return '你现在最重要的事不是证明自己没事，而是让现实里有人知道你正在经历什么。'
  }

  if (latestAssistantMessage.value?.content.includes('一分钟')) {
    return '你不是一个需要立刻被修好的人。先照顾这一分钟，已经是一种很认真地活着。'
  }

  return '你不是一个需要立刻被修好的人。能把心里的重量说出来，本身就是在给自己留一盏灯。'
})

const realWorldSupportMessage = computed(() => {
  if (store.riskLevel === 'L2' || store.riskLevel === 'L3') {
    return '我现在不太安全，需要你立刻联系我或陪我待一会儿。如果你方便，请现在给我打电话，或帮我联系附近可信任的人。'
  }

  return '我现在状态不太好，不需要你解决问题，但能不能陪我待一会儿？如果方便的话，请给我打个电话，或者陪我聊十分钟。'
})

const riskBanner = computed(() => {
  if (store.riskLevel === 'L3') {
    return {
      type: 'error' as const,
      title: '先保证现实安全',
      description: '如果你担心自己或他人会受到伤害，请立刻联系当地急救或危机热线，并尽量让可信任的人陪在身边。'
    }
  }

  if (store.riskLevel === 'L2') {
    return {
      type: 'warning' as const,
      title: '智小渡会先帮你稳定',
      description: store.riskSummary || '当前压力信号较高，系统会优先安排稳定和安全相关的回应。'
    }
  }

  return null
})

const assistantAvatarStyle = {
  background: '#3bb36b',
  color: '#fff'
}

const modeLabel = (mode?: DuxinMode | string) => {
  const labels: Record<string, string> = {
    support: '情绪支持',
    relationship: '关系梳理',
    growth: '行动整理',
    crisis: '先稳定'
  }
  return labels[mode || 'support'] || '情绪支持'
}

const modeTagColor = (mode?: DuxinMode | string) => {
  const colors: Record<string, string> = {
    support: 'cyan',
    relationship: 'blue',
    growth: 'green',
    crisis: 'orange'
  }
  return colors[mode || 'support'] || 'cyan'
}

const formatTime = (value?: string | null) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const renderMarkdown = (content: string) => marked.parse(content || '') as string

const messageAvatarStyle = (role: DuxinMessage['role']) => {
  if (role === 'user') {
    return {
      background: '#3bb36b',
      color: '#fff'
    }
  }
  return assistantAvatarStyle
}

const assistantInitial = (item: DuxinMessage) => speakerName(item).slice(0, 1) || '渡'

const speakerName = (item: DuxinMessage) => {
  if (item.role === 'user') return '你'
  const team = item.metadata?.team
  const counselor = team?.members?.find(member => member.key !== 'zhidu')
  return counselor?.name || item.agent_name || '智小渡'
}

const getCounselorAvatarSrc = (member?: DuxinTeamMember | null) => {
  if (!member) return ''
  return generatePersonaAvatar(member.name, member.focus, member.style)
}

const getMessageAvatarSrc = (item: DuxinMessage) => {
  if (item.role === 'user') return userAvatarSrc.value
  const team = item.metadata?.team
  const counselor = team?.members?.find(member => member.key !== 'zhidu')
  if (counselor) return getCounselorAvatarSrc(counselor)
  return generatePersonaAvatar(speakerName(item), item.agent_name || 'duxin', 'conversation')
}

const streamingAssistantAvatarSrc = computed(() => {
  return getCounselorAvatarSrc(assignedCounselor.value) || generatePersonaAvatar('智小渡', 'support', 'streaming')
})

const scrollToBottom = async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

const applyPreset = (preset: IntakePreset) => {
  draftMode.value = preset.mode
  store.setMode(preset.mode)
  draft.value = draft.value.trim() ? `${draft.value.trim()}\n${preset.prompt}` : preset.prompt
  nextTick(() => composerRef.value?.focus?.())
}

const applyCompanionChoice = (choice: CompanionChoice) => {
  activeCompanionKey.value = choice.key
  draftMode.value = choice.mode
  store.setMode(choice.mode)

  if (!draft.value.trim()) {
    draft.value = choice.prompt
  }

  nextTick(() => composerRef.value?.focus?.())
}

const copySupportMessage = async () => {
  try {
    await navigator.clipboard.writeText(realWorldSupportMessage.value)
    message.success('已复制，可以发给一个可信任的人')
  } catch {
    message.info('可以直接选中这段短信发送给可信任的人')
  }
}

const handleComposerEnter = (event: KeyboardEvent) => {
  if (event.shiftKey) return
  event.preventDefault()
  handleSend()
}

const handleSend = async () => {
  const text = draft.value.trim()
  if (!text || store.streaming) return

  try {
    store.setMode(draftMode.value)
    draft.value = ''
    await store.sendMessage(text)
    await scrollToBottom()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '智小渡暂时无法回应，请稍后再试')
  }
}

const handleRefresh = async () => {
  await store.fetchSessions(false)
  if (store.currentSession) {
    await store.fetchMessages(store.currentSession.id)
  }
}

const handleOpenSession = async (sessionId: number) => {
  await store.openSession(sessionId)
  draftMode.value = store.currentSession?.mode || 'support'
  await scrollToBottom()
}

const handleArchiveCurrentSession = async () => {
  try {
    await store.archiveCurrentSession()
  } catch (error) {
    message.error(error instanceof Error ? error.message : '收起会话失败')
  }
}

const startNewConversation = () => {
  store.currentSession = null
  store.messages = []
  store.teamPlan = null
  store.composerStatus = ''
  store.riskLevel = 'L0'
  draftMode.value = 'support'
  activeCompanionKey.value = 'stay'
  nextTick(() => composerRef.value?.focus?.())
}

watch(
  () => store.messages.length,
  () => {
    scrollToBottom()
  }
)

watch(
  () => store.currentSession?.mode,
  mode => {
    if (mode) draftMode.value = mode
  }
)

onMounted(async () => {
  await store.fetchSessions(false)
  await nextTick()
  composerRef.value?.focus?.()
})
</script>

<style scoped>
.duxin-page {
  max-width: 1280px;
  min-height: 100vh;
  margin: 0 auto;
  padding: 24px;
  color: #213547;
  background: transparent;
}

.duxin-hero,
.duxin-flow,
.conversation-card,
.history-strip,
.safety-note,
.risk-alert {
  max-width: 100%;
  margin: 0 auto;
}

.duxin-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 24px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 64px;
  height: 64px;
  border-radius: 16px;
  color: #fff;
  font-size: 28px;
  font-weight: 800;
  background: #3bb36b;
  box-shadow: 0 4px 15px rgba(59, 179, 107, 0.3);
}

.header-title {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.title {
  color: #1a1d1e;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: 0;
}

.subtitle {
  max-width: 760px;
  margin-top: 6px;
  color: #6b7280;
  font-size: 14px;
  line-height: 1.65;
}

.section-kicker,
.status-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #3bb36b;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0;
}

.hero-status {
  min-width: 224px;
  padding: 16px 18px;
  border: 1px solid rgba(59, 179, 107, 0.14);
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.hero-status strong {
  display: block;
  margin-top: 5px;
  color: #1a1d1e;
  font-size: 17px;
}

.risk-alert {
  margin-bottom: 18px;
  border-radius: 12px;
}

.duxin-flow {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 20px;
  align-items: stretch;
}

.intake-card,
.assignment-card,
.conversation-card,
.history-strip,
.safety-note {
  border: none;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.intake-card {
  padding: 24px;
}

.step-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 26px;
}

.flow-step {
  display: flex;
  gap: 12px;
  min-height: 74px;
  padding: 14px;
  border: 1px solid #e8f0ea;
  border-radius: 12px;
  background: #f8faf8;
  transition: all 0.3s ease;
}

.flow-step.active {
  border-color: rgba(59, 179, 107, 0.22);
  background: rgba(59, 179, 107, 0.14);
  box-shadow: 0 8px 22px rgba(59, 179, 107, 0.1);
}

.flow-step span {
  color: #3bb36b;
  font-weight: 800;
}

.flow-step strong,
.flow-step small {
  display: block;
}

.flow-step strong {
  color: #1a1d1e;
}

.flow-step small {
  margin-top: 2px;
  color: #787f84;
}

.intake-head h2,
.assignment-card h2,
.conversation-head h2 {
  margin: 6px 0 8px;
  color: #1a1d1e;
  letter-spacing: 0;
}

.intake-head p,
.assignment-card p,
.empty-conversation p,
.safety-note p {
  margin: 0;
  color: #6b7280;
  line-height: 1.75;
}

.companion-panel {
  margin-top: 22px;
  padding: 18px;
  border: 1px solid rgba(52, 105, 99, 0.12);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
}

.companion-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.companion-heading h3 {
  margin: 0;
  color: #1f3d3a;
  font-size: 18px;
  letter-spacing: 0;
}

.companion-options {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.companion-option {
  min-height: 104px;
  padding: 14px;
  border: 1px solid rgba(59, 179, 107, 0.12);
  border-radius: 12px;
  text-align: left;
  background: rgba(255, 255, 255, 0.72);
  cursor: pointer;
  transition: all 0.24s ease;
}

.companion-option strong,
.companion-option span {
  display: block;
}

.companion-option strong {
  color: #223532;
  font-size: 14px;
}

.companion-option span {
  margin-top: 8px;
  color: #65716f;
  font-size: 12px;
  line-height: 1.55;
}

.companion-option.active,
.companion-option:hover {
  border-color: rgba(52, 105, 99, 0.34);
  background: #ffffff;
  box-shadow: 0 10px 24px rgba(52, 105, 99, 0.1);
  transform: translateY(-1px);
}

.preset-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 22px 0 14px;
}

.preset-chip {
  height: 36px;
  padding: 0 14px;
  border: 1px solid #d4e8d9;
  border-radius: 999px;
  color: #3bb36b;
  background: #ebf7ee;
  cursor: pointer;
  transition: all 0.3s ease;
}

.preset-chip:hover {
  border-color: #a8d5b5;
  color: #2fa15c;
  background: #dff0e3;
  transform: translateY(-1px);
}

.intake-input {
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.7;
}

.intake-actions,
.conversation-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.intake-actions {
  margin-top: 16px;
}

.composer-state {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #6b7280;
  font-size: 14px;
}

.state-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #a8b7c4;
}

.state-dot.active {
  background: #3bb36b;
  box-shadow: 0 0 0 6px rgba(59, 179, 107, 0.16);
}

.action-buttons,
.conversation-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.send-button {
  min-width: 142px;
  border-radius: 12px;
  border: none;
  font-weight: 600;
  background: #3bb36b;
  box-shadow: 0 4px 15px rgba(59, 179, 107, 0.3);
}

.send-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(59, 179, 107, 0.4);
}

.assignment-card {
  padding: 24px;
}

.assignment-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.counselor-avatar,
.waiting-mark {
  display: grid;
  place-items: center;
  width: 72px;
  height: 72px;
  margin: 28px 0 18px;
  border-radius: 18px;
  color: #fff;
  font-size: 28px;
  font-weight: 800;
  background: #3bb36b;
}

.counselor-avatar img,
.message-avatar :deep(.ant-avatar img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.waiting-mark {
  color: #3bb36b;
  background: #ebf7ee;
  font-size: 30px;
}

.assignment-reason {
  padding-bottom: 18px;
  border-bottom: 1px solid #f0f0f0;
}

.counselor-detail {
  display: grid;
  gap: 4px;
  padding: 14px 0 0;
}

.counselor-detail span {
  color: #787f84;
  font-size: 12px;
}

.counselor-detail strong {
  color: #1a1d1e;
  font-weight: 700;
}

.team-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 18px;
}

.team-line span {
  padding: 6px 10px;
  border-radius: 999px;
  color: #3bb36b;
  background: #ebf7ee;
  font-size: 12px;
}

.conversation-card {
  margin-top: 20px;
  padding: 22px;
}

.messages {
  max-height: 560px;
  overflow-y: auto;
  margin-top: 18px;
  padding: 4px 4px 8px;
}

.empty-conversation {
  display: grid;
  place-items: center;
  min-height: 220px;
  text-align: center;
  color: #787f84;
}

.empty-conversation :deep(svg) {
  width: 34px;
  height: 34px;
  margin-bottom: 8px;
  color: #3bb36b;
}

.empty-conversation h3 {
  margin: 8px 0;
  color: #1a1d1e;
}

.message-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  gap: 12px;
  margin: 18px 0;
}

.message-row.user {
  grid-template-columns: minmax(0, 1fr) 42px;
}

.message-row.user .message-avatar {
  grid-column: 2;
}

.message-row.user .message-body {
  grid-column: 1;
  grid-row: 1;
  align-items: flex-end;
}

.message-avatar {
  margin-top: 24px;
}

.message-body {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 6px;
  color: #94a3b8;
  font-size: 12px;
}

.message-meta strong {
  color: #334155;
}

.message-bubble {
  max-width: min(760px, 100%);
  padding: 14px 16px;
  border-radius: 16px;
  color: #24384a;
  background: #f8faf8;
  line-height: 1.75;
}

.message-bubble.user {
  color: #fff;
  background: #3bb36b;
  box-shadow: 0 10px 24px rgba(59, 179, 107, 0.18);
}

.message-bubble :deep(p) {
  margin: 0 0 8px;
}

.message-bubble :deep(p:last-child) {
  margin-bottom: 0;
}

.typing {
  display: inline-flex;
  gap: 6px;
}

.typing span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #3bb36b;
  animation: typingPulse 1s infinite ease-in-out;
}

.typing span:nth-child(2) {
  animation-delay: 0.14s;
}

.typing span:nth-child(3) {
  animation-delay: 0.28s;
}

.history-strip {
  display: flex;
  align-items: stretch;
  gap: 12px;
  margin-top: 20px;
  padding: 16px;
  overflow-x: auto;
}

.history-title {
  flex: 0 0 220px;
}

.history-title strong {
  display: block;
  margin-top: 4px;
  color: #1a1d1e;
}

.history-item {
  min-width: 210px;
  padding: 12px;
  border: 1px solid #e8f0ea;
  border-radius: 12px;
  text-align: left;
  background: #f8faf8;
  cursor: pointer;
  transition: all 0.3s ease;
}

.history-item.active,
.history-item:hover {
  border-color: rgba(59, 179, 107, 0.22);
  background: #ebf7ee;
  transform: translateY(-1px);
}

.history-item span,
.history-item small {
  display: block;
}

.history-item span {
  color: #1a1d1e;
  font-weight: 700;
}

.history-item small {
  margin-top: 4px;
  color: #787f84;
}

.human-care-strip {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 16px;
  margin-top: 20px;
}

.heart-light-card,
.support-message-card {
  padding: 20px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
}

.heart-light-card {
  border-left: 4px solid #7ac7b4;
}

.heart-light-card p,
.support-message-card p {
  margin: 10px 0;
  color: #213547;
  font-size: 16px;
  line-height: 1.75;
}

.heart-light-card small {
  color: #71807d;
  line-height: 1.65;
}

.support-message-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: rgba(255, 255, 255, 0.93);
}

.plain-tool-button {
  flex: 0 0 auto;
  height: 38px;
  padding: 0 14px;
  border: 1px solid rgba(52, 105, 99, 0.22);
  border-radius: 10px;
  color: #346963;
  background: #fff;
  cursor: pointer;
  transition: all 0.24s ease;
}

.plain-tool-button:hover {
  border-color: rgba(52, 105, 99, 0.42);
  background: #f4fbf8;
}

.safety-note {
  margin-top: 20px;
  padding: 16px 18px;
  display: grid;
  grid-template-columns: 100px minmax(0, 1fr);
  gap: 16px;
}

.safety-note strong {
  color: #d46b08;
}

@keyframes typingPulse {
  0%,
  80%,
  100% {
    opacity: 0.28;
    transform: translateY(0);
  }
  40% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

@media (max-width: 980px) {
  .duxin-page {
    padding: 18px;
  }

  .duxin-hero,
  .duxin-flow,
  .human-care-strip,
  .safety-note {
    display: grid;
    grid-template-columns: 1fr;
  }

  .duxin-hero {
    align-items: start;
  }

  .hero-status {
    min-width: 0;
  }
}

@media (max-width: 680px) {
  .duxin-page {
    padding: 16px;
  }

  .header-content {
    align-items: flex-start;
  }

  .header-icon {
    width: 56px;
    height: 56px;
    border-radius: 14px;
    font-size: 24px;
  }

  .title {
    font-size: 24px;
  }

  .subtitle {
    font-size: 13px;
  }

  .intake-card,
  .assignment-card,
  .conversation-card {
    padding: 16px;
  }

  .step-row {
    grid-template-columns: 1fr;
  }

  .companion-heading,
  .intake-actions,
  .conversation-head,
  .support-message-card,
  .history-strip {
    display: grid;
  }

  .companion-options {
    grid-template-columns: 1fr;
  }

  .action-buttons,
  .conversation-tools {
    width: 100%;
  }

  .action-buttons .ant-btn,
  .conversation-tools .ant-btn {
    flex: 1;
  }

  .message-row,
  .message-row.user {
    grid-template-columns: 36px minmax(0, 1fr);
  }

  .message-row.user .message-avatar {
    grid-column: 1;
  }

  .message-row.user .message-body {
    grid-column: 2;
    align-items: flex-start;
  }

  .safety-note {
    grid-template-columns: 1fr;
  }
}
</style>
