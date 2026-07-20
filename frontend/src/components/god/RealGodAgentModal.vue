<template>
  <a-modal
    v-model:open="visible"
    title="智能体生成助手"
    width="1000px"
    :footer="null"
    @cancel="handleCancel"
    class="god-agent-modal"
    :bodyStyle="{ padding: 0, height: '80vh' }"
    centered
  >
    <div class="god-agent-container">
      <div class="chat-window" ref="chatWindowRef">
        <div v-for="(msg, index) in messages" :key="index" class="message-item" :class="msg.role">
          <div class="avatar">
            <a-avatar v-if="msg.role === 'assistant'" style="background-color: #faad14">
              <img :src="assistantAvatarSrc" alt="智能体生成助手" />
            </a-avatar>
            <a-avatar v-else style="background-color: #3bb36b">
              <img v-if="userAvatarSrc" :src="userAvatarSrc" :alt="authStore.user?.username || '用户'" />
              <template v-else>{{ getAvatarInitial(authStore.user?.username, 'U') }}</template>
            </a-avatar>
          </div>
          <div class="content-wrapper">
            <!-- User Message -->
            <div v-if="msg.role === 'user'" class="bubble user-bubble">
              {{ msg.content }}
            </div>

            <!-- Assistant Message (Structured Items) -->
            <template v-else>
               <!-- Fallback for simple content -->
               <div v-if="msg.content && (!msg.items || msg.items.length === 0)" class="bubble">
                 {{ msg.content }}
               </div>

               <!-- Structured Items -->
               <div v-for="(item, i) in msg.items" :key="i" class="msg-item">
                  
                 <!-- 1. Normal Text -->
                 <div v-if="item.type === 'text'" class="bubble">
                   {{ item.content }}
                 </div>

                 <!-- 2. Search Intent (Thought) -->
                 <div v-else-if="item.type === 'thought'" class="bubble thought-bubble">
                   <div class="thought-header">
                      <span class="icon">💭</span> 思考过程
                   </div>
                   <div class="thought-content">{{ item.content }}</div>
                 </div>

                 <!-- 3. Searching State -->
                 <div v-else-if="item.type === 'search'" class="search-block">
                   <div class="search-status">
                      <span v-if="item.status === 'loading'" class="icon loading">🔍</span>
                      <span v-else class="icon success">✓</span>
                     <span class="status-text">
                        {{ item.status === 'loading' ? '正在搜索' : '搜索完成' }}: 
                       <span class="query">{{ item.query }}</span>
                     </span>
                   </div>
                   <div v-if="item.status === 'done' && item.result" class="search-result">
                     <a-collapse ghost size="small">
                         <a-collapse-panel key="1" header="查看搜索结果">
                          <pre>{{ item.result }}</pre>
                        </a-collapse-panel>
                     </a-collapse>
                   </div>
                 </div>

                 <!-- 4. Generated Persona -->
                 <div v-else-if="item.type === 'persona'" class="persona-block">
                   <a-card 
                    size="small" 
                    class="persona-card"
                    :title="item.persona.name"
                   >
                     <template #extra>
                        <a-tag color="orange">{{ item.persona.title }}</a-tag>
                     </template>
                     <p class="persona-bio">{{ item.persona.bio }}</p>
                     <div class="persona-tags">
                        <a-tag v-for="t in (item.persona.theories || []).slice(0, 3)" :key="t">{{ t }}</a-tag>
                     </div>
                     <div class="actions">
                        <a-button type="primary" size="small" @click="handleViewPersona">查看详情</a-button>
                     </div>
                   </a-card>
                 </div>

                 <!-- 6. Status/Progress -->
                 <div v-else-if="item.type === 'status'" class="status-block">
                   <div class="status-content">
                     <span class="icon">⏳</span> 
                     <span class="status-text">{{ item.content }}</span>
                   </div>
                 </div>

                 <!-- 5. Error -->
                 <div v-else-if="item.type === 'error'" class="bubble error-bubble">
                   ❌ {{ item.content }}
                 </div>
               </div>
            </template>
          </div>
        </div>
        
        <div v-if="loading && (!messages[messages.length-1]?.items || messages[messages.length-1]?.items?.length === 0)" class="message-item assistant">
          <div class="avatar">
            <a-avatar style="background-color: #faad14">
              <img :src="assistantAvatarSrc" alt="智能体生成助手" />
            </a-avatar>
          </div>
          <div class="content-wrapper">
            <div class="bubble loading">
              <a-spin size="small" /> 正在调用助手...
            </div>
          </div>
        </div>
      </div>

      <div class="input-area">
        <a-textarea
          v-model:value="input"
          placeholder="描述您想要创建的智能体... (Enter 发送，Shift+Enter 换行)"
          :auto-size="{ minRows: 2, maxRows: 4 }"
          @keydown.enter.exact.prevent="handleSend"
          @keydown.ctrl.enter.prevent="handleSend"
          :disabled="loading"
          class="custom-textarea"
        />
        <a-button type="primary" class="send-btn" @click="handleSend" :loading="loading">
          <template #icon><send-outlined /></template>
          发送
        </a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, nextTick, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { usePersonaStore } from '@/stores/persona'
import { useAuthStore } from '@/stores/auth'
import { SendOutlined } from '@ant-design/icons-vue'
import { generatePersonaAvatar, getAvatarInitial, resolveBuiltInUserAvatarSrc } from '@/utils/avatar'

interface MessageItem {
  type: 'text' | 'thought' | 'search' | 'persona' | 'error' | 'status'
  content?: string
  query?: string
  result?: string
  status?: 'loading' | 'done'
  persona?: any
  current?: number
  total?: number
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content?: string
  items?: MessageItem[]
  timestamp: number
}

type StreamEvent = {
  type?: string
  content?: unknown
  current?: number
  total?: number
  [key: string]: unknown
}

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits(['update:open'])

const router = useRouter()
const personaStore = usePersonaStore()
const authStore = useAuthStore()
const input = ref('')
const chatWindowRef = ref<HTMLElement | null>(null)
const messages = ref<ChatMessage[]>([])
const loading = ref(false)
const totalToGenerate = ref(1)
const assistantAvatarSrc = generatePersonaAvatar('智造助手', 'agent-builder', 'real-god')
const userAvatarSrc = computed(() => resolveBuiltInUserAvatarSrc(authStore.user))

const visible = computed({
  get: () => props.open,
  set: (val) => emit('update:open', val)
})

const scrollToBottom = () => {
  nextTick(() => {
    if (chatWindowRef.value) {
      chatWindowRef.value.scrollTop = chatWindowRef.value.scrollHeight
    }
  })
}

const ensureWelcomeMessage = () => {
  if (messages.value.length === 0) {
    messages.value.push({
      role: 'assistant',
      content: '',
      items: [
        {
          type: 'text',
          content: '我是智能体生成助手。你可以描述一个人设、职业方向或研究主题，我会帮你生成可保存的智能体角色。'
        }
      ],
      timestamp: Date.now()
    })
  }
}

const appendStatus = (items: MessageItem[], content: string) => {
  const lastStatus = [...items].reverse().find(i => i.type === 'status')
  if (lastStatus) {
    lastStatus.content = content
  } else {
    items.push({ type: 'status', content })
  }
}

const appendThought = (items: MessageItem[], content: string) => {
  const lastItem = items[items.length - 1]
  if (lastItem && lastItem.type === 'thought') {
    lastItem.content = (lastItem.content || '') + content
  } else {
    items.push({ type: 'thought', content })
  }
}

watch(() => props.open, (val) => {
  if (val) {
    ensureWelcomeMessage()
    scrollToBottom()
  }
})

watch(() => messages.value.length, scrollToBottom)
watch(() => messages.value[messages.value.length - 1]?.items, scrollToBottom, { deep: true })

const handleSend = async () => {
  if (!input.value.trim() || loading.value) return

  const prompt = input.value
  input.value = ''

  messages.value.push({
    role: 'user',
    content: prompt,
    timestamp: Date.now()
  })

  loading.value = true
  totalToGenerate.value = 1

  const assistantMsg: ChatMessage = {
    role: 'assistant',
    items: [],
    timestamp: Date.now()
  }
  messages.value.push(assistantMsg)

  try {
    const response = await fetch('/api/v1/god/generate_real', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${localStorage.getItem('token') || ''}`
      },
      body: JSON.stringify({ prompt, n: 1 })
    })

    if (!response.ok) {
      const detail = await response.text().catch(() => '')
      throw new Error(detail || `HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    if (!reader) throw new Error('No reader')

    const decoder = new TextDecoder()
    let buffer = ''
    const items = assistantMsg.items ?? (assistantMsg.items = [])

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      const parts = buffer.split('\n\n')
      buffer = parts.pop() || ''

      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data: ')) continue

        const jsonStr = line.slice(6).trim()
        if (!jsonStr || jsonStr === '[DONE]') continue

        let event: StreamEvent
        try {
          event = JSON.parse(jsonStr)
        } catch (e) {
          console.error('JSON parse error', e)
          continue
        }

        const eventType = event.type || 'text'
        const content = event.content

        if (eventType === 'count') {
          totalToGenerate.value = Number(content) || totalToGenerate.value
        } else if (eventType === 'progress') {
          if (typeof event.total === 'number') totalToGenerate.value = event.total
          appendStatus(items, `正在生成第 ${event.current ?? '?'} 个，进度 ${event.current ?? '?'} / ${event.total ?? '?'}`)
        } else if (eventType === 'status' || eventType === 'thought_start') {
          appendStatus(items, typeof content === 'string' ? content : '正在处理...')
        } else if (eventType === 'thought' || eventType === 'thought_chunk') {
          if (typeof content === 'string' && content.trim()) {
            appendThought(items, content)
          }
        } else if (eventType === 'action') {
          const text = typeof content === 'string' ? content : ''
          if (text.includes('Search')) {
            const query = text.replace(/Search[:：\[\]]/g, '').trim()
            items.push({ type: 'search', query: query || text, status: 'loading', result: '' })
          }
        } else if (eventType === 'observation') {
          const searchItem = [...items].reverse().find(i => i.type === 'search' && i.status === 'loading')
          if (searchItem) {
            searchItem.status = 'done'
            searchItem.result = typeof content === 'string' ? content : JSON.stringify(content)
          } else {
            items.push({ type: 'text', content: `[Observation] ${String(content ?? '')}` })
          }
        } else if (eventType === 'result') {
          const results = Array.isArray(content) ? content : content ? [content] : []
          for (const p of results) {
            items.push({ type: 'persona', persona: p })
          }
          items.push({
            type: 'text',
            content: results.length ? `完成，共生成 ${results.length} 个角色。` : '生成完成。'
          })
        } else if (eventType === 'error') {
          const errorContent = typeof content === 'string' ? content : '生成失败'
          items.push({ type: 'error', content: errorContent })
          message.error(errorContent)
        } else if (typeof content === 'string' && content.trim()) {
          appendThought(items, content)
        }

        scrollToBottom()
      }
    }

    if (!assistantMsg.items || assistantMsg.items.length === 0) {
      assistantMsg.items = [{ type: 'text', content: '生成完成。' }]
    }
  } catch (error: any) {
    assistantMsg.items?.push({ type: 'error', content: error.message || '生成失败' })
  } finally {
    loading.value = false
  }
}

const handleCancel = () => {
  visible.value = false
}

const handleViewPersona = () => {
  visible.value = false
  personaStore.fetchPersonas()
  router.push('/personas')
}

watch(visible, (newVal) => {
  if (!newVal && messages.value.some(m => m.items?.some(i => i.type === 'persona'))) {
    personaStore.fetchPersonas()
  }
})
</script>

<style scoped>
.god-agent-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  border-radius: 0;
}

.chat-window {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f5f7f9;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message-item {
  display: flex;
  gap: 12px;
  max-width: 95%;
}

.message-item.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-item.assistant {
  align-self: flex-start;
}

.avatar :deep(.ant-avatar img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  /* Ensure bubbles don't stretch too wide if content is short */
  align-items: flex-start; 
}

.message-item.user .content-wrapper {
  align-items: flex-end;
}

.bubble {
  padding: 12px 16px;
  border-radius: 12px 12px 12px 0;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
  max-width: 100%;
}

.user-bubble {
  background: #3bb36b;
  color: #fff;
  border-radius: 12px 12px 0 12px;
  box-shadow: 0 2px 6px rgba(24, 144, 255, 0.2);
}

.thought-bubble {
  background: #fafafa;
  border: 1px solid #ebebeb;
  border-left: 4px solid #faad14;
  color: #555;
  font-size: 13px;
  width: 100%;
  border-radius: 8px;
}

.thought-header {
  font-weight: 500;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.search-block {
  background: #f0faff;
  border: 1px solid #bae7ff;
  border-radius: 8px;
  padding: 10px 14px;
  width: 100%;
  font-size: 13px;
}

.search-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-text {
  flex: 1;
}

.query {
  font-weight: 500;
  color: #3bb36b;
}

.search-result {
  margin-top: 8px;
  background: #fff;
  border-radius: 4px;
  overflow: hidden;
}

.persona-block {
  width: 100%;
}

.error-bubble {
  background: #fff1f0;
  border: 1px solid #ffa39e;
  color: #cf1322;
}

.status-block {
  width: 100%;
  margin: 8px 0;
  text-align: center;
}

.status-content {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  color: #52c41a;
  font-weight: 500;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}

.loading {
  font-style: italic;
  color: #8c8c8c;
}

.persona-card {
  width: 100%;
  margin-bottom: 8px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  border: 1px solid #f0f0f0;
}

.persona-card :deep(.ant-card-head) {
  background: #fafafa;
  border-bottom: 1px solid #f0f0f0;
}

.persona-bio {
  font-size: 12px;
  color: #666;
  margin: 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.persona-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}

.input-area {
  padding: 16px;
  display: flex;
  gap: 12px;
  align-items: flex-end;
  border-top: 1px solid #f0f0f0;
  margin-top: 0;
  background: #fff;
  flex-shrink: 0;
}

.custom-textarea {
  border-radius: 8px;
  resize: none;
  padding: 8px 12px;
  transition: all 0.3s;
}

.custom-textarea:hover, .custom-textarea:focus {
  border-color: #3bb36b;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.1);
}

.send-btn {
  height: 40px;
  padding: 0 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
