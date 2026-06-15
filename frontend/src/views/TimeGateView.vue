<template>
  <div class="time-gate-page">
    <div class="page-orb orb-left"></div>
    <div class="page-orb orb-right"></div>
    <a-layout class="chat-layout">
      <!-- 左侧智能体列表 -->
      <a-layout-sider width="280" class="sider-section">
        <div class="sider-header">
          <div>
            <h3 class="sider-title">我的智能体</h3>
            <p class="sider-subtitle">选择一个角色，进入时空对话</p>
          </div>
          <a-button type="primary" size="small" ghost @click="handleAddAgent">
            <plus-outlined /> 新增
          </a-button>
        </div>
        
        <div class="agent-list">
          <div 
            v-for="agent in personaStore.personas" 
            :key="agent.id"
            class="agent-item"
            :class="{ active: currentAgent?.id === agent.id }"
            @click="switchAgent(agent)"
          >
            <a-avatar size="small" :style="{ background: getAvatarGradient(agent.name) }">
              {{ agent.name[0] }}
            </a-avatar>
            <div class="agent-info">
              <div class="agent-name">{{ agent.name }}</div>
              <div class="agent-title">{{ agent.title }}</div>
            </div>
            <a-dropdown :trigger="['click']">
              <more-outlined class="more-icon" />
              <template #overlay>
                <a-menu>
                  <a-menu-item key="1">查看详情</a-menu-item>
                  <a-menu-item key="2" danger>删除对话</a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>
          
          <div v-if="personaStore.personas.length === 0 && !personaStore.loading" class="empty-agent">
            <a-empty description="暂无智能体，请先去智能体工坊创建" />
          </div>
        </div>
      </a-layout-sider>
      
      <!-- 右侧对话区 -->
      <a-layout class="chat-section">
        <div v-if="!currentAgent" class="chat-welcome">
          <div class="welcome-card">
            <div class="welcome-avatar">⌛</div>
            <h2>欢迎来到时空之门</h2>
            <p>选择左侧的智能体，开始跨时空对话</p>
            <div class="welcome-badges">
              <span class="welcome-badge">流式回复</span>
              <span class="welcome-badge">图片发送</span>
              <span class="welcome-badge">清空重开</span>
            </div>
          </div>
        </div>
        
        <div v-else class="chat-container">
          <!-- 对话头部 -->
          <div class="chat-header">
            <div class="current-agent-info">
              <a-avatar size="small" :style="{ background: getAvatarGradient(currentAgent.name) }">
                {{ currentAgent.name[0] }}
              </a-avatar>
              <div class="agent-meta">
                <span class="agent-name">{{ currentAgent.name }}</span>
                <span class="agent-title">{{ currentAgent.title }}</span>
                <span class="agent-bio">{{ currentAgentBio }}</span>
              </div>
            </div>
            <div class="header-actions">
              <span class="status-pill" :class="{ loading }">
                {{ loading ? '生成中' : currentConversationSummary }}
              </span>
              <a-button type="text" size="small" @click="clearChat">
                <delete-outlined /> 清空对话
              </a-button>
            </div>
          </div>
          
          <!-- 对话消息 -->
          <div class="messages-container" ref="messagesContainer">
            <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.role">
              <div v-if="msg.role === 'assistant'" class="message-avatar">
                <a-avatar size="small" :style="{ background: getAvatarGradient(currentAgent.name) }">
                  {{ currentAgent.name[0] }}
                </a-avatar>
              </div>
              <div class="message-content">
                <div class="message-bubble" v-html="formatMessage(msg.content)"></div>
                <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
              </div>
              <div v-if="msg.role === 'user'" class="message-avatar">
                <a-avatar size="small" style="background: #667eea">
                  {{ authStore.user?.username?.[0] || '我' }}
                </a-avatar>
              </div>
            </div>
            
            <div v-if="loading" class="message-item assistant">
              <div class="message-avatar">
                <a-avatar size="small" :style="{ background: getAvatarGradient(currentAgent.name) }">
                  {{ currentAgent.name[0] }}
                </a-avatar>
              </div>
              <div class="message-content">
                <div class="message-bubble thinking">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 输入框 -->
          <div class="input-section">
            <div class="input-toolbar">
              <a-button type="text" size="small" @click="triggerImageUpload">
                <picture-outlined /> 上传图片
              </a-button>
              <input 
                ref="imageInput" 
                type="file" 
                accept="image/*" 
                style="display: none" 
                @change="handleImageUpload"
              />
              <span class="tip-text">支持粘贴图片（Ctrl+V）直接发送，上传后会自动转为可发送内容</span>
            </div>
            <a-textarea
              v-model:value="inputMessage"
              :rows="3"
              placeholder="请输入消息，按 Enter 发送，Shift+Enter 换行，支持粘贴图片"
              @keydown.enter="handleSend"
              @paste="handlePaste"
              :disabled="loading"
              class="chat-input"
            />
            <div class="input-actions">
              <a-button 
                type="primary" 
                @click="handleSend" 
                :loading="loading"
                :disabled="(!inputMessage.trim() && !uploadingImage) || !currentAgent"
              >
                <send-outlined /> 发送
              </a-button>
            </div>
          </div>
        </div>
      </a-layout>
    </a-layout>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePersonaStore } from '@/stores/persona'
import { useAuthStore } from '@/stores/auth'
import {
  PlusOutlined,
  MoreOutlined,
  SendOutlined,
  DeleteOutlined,
  PictureOutlined
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import request from '@/utils/request'
import { marked } from 'marked'

const personaStore = usePersonaStore()
const authStore = useAuthStore()
const router = useRouter()

const currentAgent = ref<any>(null)
const messages = ref<Array<{ role: 'user' | 'assistant', content: string, timestamp: number, isWelcome?: boolean }>>([])
const inputMessage = ref('')
const loading = ref(false)
const uploadingImage = ref(false)
const messagesContainer = ref<HTMLElement | null>(null)
const imageInput = ref<HTMLInputElement | null>(null)
const currentAgentBio = computed(() => currentAgent.value?.bio?.trim() || '这位智能体还没有写简介。')
const currentConversationSummary = computed(() => {
  const userMessages = messages.value.filter(msg => !msg.isWelcome)
  return `${userMessages.length} 条消息`
})

const getAvatarGradient = (name: string) => {
  const colors = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b', '#fa709a', '#fee140', '#30cfd0']
  return colors[name.charCodeAt(0) % colors.length]
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const welcomeMessage = (agent: any) => ({
  role: 'assistant' as const,
  content: `你好，我是 ${agent.name}。${agent.bio || '很高兴和你交流。'}`,
  timestamp: Date.now(),
  isWelcome: true
})

const handleAddAgent = () => {
  message.info('请先去智能体工坊创建智能体')
  router.push('/personas')
}

const switchAgent = async (agent: any) => {
  currentAgent.value = agent
  messages.value = []
  inputMessage.value = ''
  loading.value = true

  try {
    const res = await request.get('/agents/chat/history/' + agent.id)
    if (res.data && res.data.length > 0) {
      messages.value = res.data
    } else {
      messages.value.push(welcomeMessage(agent))
    }
  } catch (error) {
    console.error('加载历史对话失败:', error)
    messages.value.push(welcomeMessage(agent))
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

const handleSend = async (e?: KeyboardEvent) => {
  if (e && e.shiftKey) return
  e?.preventDefault()

  if (!currentAgent.value) {
    message.warning('请先选择一个智能体')
    return
  }

  const content = inputMessage.value.trim()
  if (!content) return

  messages.value.push({ role: 'user', content, timestamp: Date.now() })
  inputMessage.value = ''
  loading.value = true

  const assistantMsgIndex = messages.value.length
  messages.value.push({ role: 'assistant', content: '', timestamp: Date.now() })

  await nextTick()
  scrollToBottom()

  try {
    await request.post('/agents/chat/message', {
      persona_id: currentAgent.value.id,
      role: 'user',
      content
    })

    const contextMessages = messages.value
      .slice(0, -1)
      .filter(msg => !msg.isWelcome && msg.content.trim().length > 0)
      .map(msg => ({
        role: msg.role,
        speaker: msg.role === 'user' ? '用户' : currentAgent.value.name,
        content: msg.content
      }))

    const response = await fetch('/api/v1/agents/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + (authStore.token || '')
      },
      body: JSON.stringify({
        agent_name: currentAgent.value.name,
        persona_json: currentAgent.value,
        context_messages: contextMessages,
        theme: '自由对话'
      })
    })

    if (!response.ok) {
      const detail = await response.text().catch(() => '')
      throw new Error(detail || '网络请求失败')
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('未能读取流式响应')
    }

    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''

      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data: ')) continue

        const data = line.slice(6).trim()
        if (!data || data === '[DONE]') continue

        try {
          const parsed = JSON.parse(data)
          if (parsed.content) {
            messages.value[assistantMsgIndex].content += parsed.content
            await nextTick()
            scrollToBottom()
          } else if (parsed.error) {
            throw new Error(parsed.error)
          }
        } catch (parseError) {
          console.error('解析流式响应失败:', parseError)
        }
      }
    }

    if (!messages.value[assistantMsgIndex].content.trim()) {
      messages.value[assistantMsgIndex].content = '抱歉，时空之门暂时无法调用模型服务，请检查后端 API_KEY / BASE_URL 配置后再试。'
    }

    await request.post('/agents/chat/message', {
      persona_id: currentAgent.value.id,
      role: 'assistant',
      content: messages.value[assistantMsgIndex].content
    })
  } catch (error) {
    console.error('对话失败:', error)
    message.error('对话失败，请稍后重试')
    messages.value[assistantMsgIndex].content = error instanceof Error && error.message
      ? error.message
      : '抱歉，时空之门暂时无法回答这个问题。'

    await request.post('/agents/chat/message', {
      persona_id: currentAgent.value.id,
      role: 'assistant',
      content: messages.value[assistantMsgIndex].content
    })
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

const clearChat = async () => {
  if (!currentAgent.value) return

  try {
    await request.delete('/agents/chat/history/' + currentAgent.value.id)
    inputMessage.value = ''
    messages.value = [welcomeMessage(currentAgent.value)]
    message.success('对话历史已清空')
    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error('清空对话失败:', error)
    message.error('清空对话失败，请稍后重试')
  }
}

const formatMessage = (content: string) => marked.parse(content)

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.getHours().toString().padStart(2, '0') + ':' + date.getMinutes().toString().padStart(2, '0')
}

const triggerImageUpload = () => {
  imageInput.value?.click()
}

const uploadAndInsertImage = async (file: File) => {
  if (!file.type.startsWith('image/')) {
    message.error('请选择图片文件')
    return
  }

  if (file.size > 10 * 1024 * 1024) {
    message.error('图片大小不能超过 10MB')
    return
  }

  uploadingImage.value = true

  try {
    const formData = new FormData()
    formData.append('file', file)

    const res = await request.post('/upload/image', formData)

    if (res.data && res.data.url) {
      inputMessage.value += `![image](${res.data.url})\n`
      message.success('图片上传成功')
    } else {
      throw new Error('上传失败，未返回图片 URL')
    }
  } catch (error) {
    console.error('图片上传失败:', error)
    message.error('图片上传失败，请稍后重试')
  } finally {
    uploadingImage.value = false
  }
}

const handleImageUpload = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  await uploadAndInsertImage(file)
  target.value = ''
}

const handlePaste = async (e: ClipboardEvent) => {
  const items = e.clipboardData?.items
  if (!items) return

  for (const item of items) {
    if (item.type.indexOf('image') !== -1) {
      e.preventDefault()
      const file = item.getAsFile()
      if (file) {
        await uploadAndInsertImage(file)
      }
      break
    }
  }
}

onMounted(() => {
  personaStore.fetchPersonas(authStore.user?.id)
})
</script>

<style scoped>
.time-gate-page {
  position: relative;
  height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(102, 126, 234, 0.16), transparent 34%),
    radial-gradient(circle at bottom right, rgba(113, 201, 206, 0.16), transparent 28%),
    linear-gradient(180deg, #f8fbff 0%, #eef3f8 100%);
  overflow: hidden;
}

.chat-layout {
  position: relative;
  z-index: 1;
  height: 100%;
}

.page-orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(4px);
  opacity: 0.55;
  pointer-events: none;
}

.orb-left {
  top: -120px;
  left: -100px;
  width: 260px;
  height: 260px;
  background: radial-gradient(circle, rgba(102, 126, 234, 0.45) 0%, rgba(102, 126, 234, 0) 70%);
}

.orb-right {
  right: -120px;
  bottom: -120px;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(113, 201, 206, 0.38) 0%, rgba(113, 201, 206, 0) 68%);
}

.sider-section {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(18px);
  border-right: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 10px 0 40px rgba(31, 41, 55, 0.08);
}

.sider-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 22px 18px 18px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
}

.sider-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: #10213a;
  letter-spacing: 0.01em;
}

.sider-subtitle {
  margin: 6px 0 0;
  font-size: 12px;
  color: #64748b;
}

.agent-list {
  padding: 10px 10px 14px;
  height: calc(100vh - 86px);
  overflow-y: auto;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 14px;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, box-shadow 0.18s ease;
}

.agent-item:hover {
  background: rgba(255, 255, 255, 0.75);
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
}

.agent-item.active {
  background: linear-gradient(135deg, #667eea 0%, #71c9ce 100%);
  color: white;
  box-shadow: 0 16px 32px rgba(102, 126, 234, 0.24);
}

.agent-info {
  flex: 1;
  overflow: hidden;
  min-width: 0;
}

.agent-name {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-title {
  font-size: 12px;
  color: #888;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-item.active .agent-title {
  color: rgba(255, 255, 255, 0.8);
}

.more-icon {
  font-size: 14px;
  color: #888;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.agent-item:hover .more-icon {
  opacity: 1;
}

.agent-item.active .more-icon {
  color: white;
  opacity: 1;
}

.empty-agent {
  padding: 40px 20px;
  text-align: center;
}

/* 对话区域 */
.chat-section {
  position: relative;
  background: transparent;
}

.chat-welcome {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #64748b;
  padding: 32px;
}

.welcome-card {
  max-width: 520px;
  width: 100%;
  padding: 32px 28px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.74);
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.9);
  text-align: center;
  backdrop-filter: blur(18px);
}

.welcome-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 84px;
  height: 84px;
  margin-bottom: 18px;
  border-radius: 50%;
  font-size: 36px;
  color: #0f172a;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(113, 201, 206, 0.28));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.chat-welcome h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #10213a;
}

.welcome-card p {
  margin: 0;
  line-height: 1.7;
}

.welcome-badges {
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}

.welcome-badge {
  padding: 8px 12px;
  border-radius: 999px;
  font-size: 12px;
  color: #334155;
  background: rgba(148, 163, 184, 0.14);
}

.chat-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 24px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  box-shadow: 0 6px 24px rgba(15, 23, 42, 0.06);
}

.current-agent-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.agent-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.agent-meta .agent-name {
  font-weight: 600;
  color: #10213a;
}

.agent-meta .agent-title {
  font-size: 13px;
  color: #64748b;
}

.agent-bio {
  margin-top: 4px;
  font-size: 12px;
  color: #94a3b8;
  max-width: 680px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  color: #1e293b;
  background: rgba(148, 163, 184, 0.14);
  border: 1px solid rgba(148, 163, 184, 0.2);
}

.status-pill.loading {
  color: #334155;
  background: rgba(102, 126, 234, 0.14);
  border-color: rgba(102, 126, 234, 0.18);
}

.messages-container {
  flex: 1;
  padding: 26px 24px 22px;
  overflow-y: auto;
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.65), transparent 40%),
    transparent;
}

.message-item {
  display: flex;
  gap: 14px;
  margin-bottom: 18px;
  align-items: flex-end;
}

.message-item.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  margin-top: 4px;
}

.message-content {
  max-width: 70%;
}

.message-bubble {
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.78);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  line-height: 1.6;
  word-break: break-word;
  backdrop-filter: blur(12px);
}

.message-bubble p {
  margin: 0 0 8px 0;
}

.message-bubble p:last-child {
  margin-bottom: 0;
}

.message-bubble ul, .message-bubble ol {
  margin: 8px 0;
  padding-left: 20px;
}

.message-bubble li {
  margin-bottom: 4px;
}

.message-bubble code {
  background: #f6f8fa;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9em;
}

.message-bubble pre {
  background: #f6f8fa;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.message-item.user .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #7c3aed 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 14px 30px rgba(102, 126, 234, 0.22);
}

.message-item.user .message-bubble code,
.message-item.user .message-bubble pre {
  background: rgba(255, 255, 255, 0.2);
}

.message-time {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
  text-align: left;
}

.message-item.user .message-time {
  text-align: right;
}

.thinking {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 16px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #888;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.input-section {
  padding: 16px 24px 20px;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(18px);
  border-top: 1px solid rgba(148, 163, 184, 0.16);
}

.input-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.tip-text {
  font-size: 12px;
  color: #94a3b8;
}

.chat-input {
  border-radius: 16px;
  margin-bottom: 12px;
  overflow: hidden;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 960px) {
  .time-gate-page {
    min-height: 100vh;
    height: auto;
    overflow: auto;
  }

  .chat-layout {
    flex-direction: column;
  }

  .sider-section {
    width: 100% !important;
    max-width: none !important;
    flex: none !important;
  }

  .agent-list {
    height: auto;
    max-height: 34vh;
  }

  .chat-header,
  .input-section,
  .messages-container {
    padding-left: 16px;
    padding-right: 16px;
  }

  .messages-container {
    padding-top: 18px;
    padding-bottom: 18px;
  }

  .message-content {
    max-width: 86%;
  }

  .header-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}
</style>


