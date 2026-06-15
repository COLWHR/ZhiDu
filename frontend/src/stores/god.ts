import { defineStore } from 'pinia'
import { message } from 'ant-design-vue'

interface Persona {
  id: number
  name: string
  title: string
  bio: string
  theories: string[]
  stance: string
  system_prompt: string
  is_public: boolean
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  personas?: Persona[]
}

type StreamPayload = {
  type?: string
  content?: unknown
  [key: string]: unknown
}

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

const readResponseDetail = async (response: Response) => {
  const raw = await response.text().catch(() => '')
  if (!raw) return `Request failed: ${response.status}`

  try {
    const parsed = JSON.parse(raw)
    return typeof parsed?.detail === 'string' ? parsed.detail : raw
  } catch {
    return raw
  }
}

export const useGodStore = defineStore('god', {
  state: () => ({
    messages: [] as ChatMessage[],
    loading: false
  }),
  actions: {
    async sendMessage(prompt: string) {
      this.messages.push({
        role: 'user',
        content: prompt,
        timestamp: Date.now()
      })

      this.loading = true
      const maxRetries = 2
      let lastError: unknown = null

      try {
        for (let retries = 0; retries <= maxRetries; retries++) {
          const assistantMessage: ChatMessage = {
            role: 'assistant',
            content: '',
            timestamp: Date.now(),
            personas: []
          }
          this.messages.push(assistantMessage)

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
              throw new Error(await readResponseDetail(response))
            }

            const reader = response.body?.getReader()
            if (!reader) {
              throw new Error('Stream response is unavailable')
            }

            const decoder = new TextDecoder()
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

                const payloadText = line.slice(6).trim()
                if (!payloadText || payloadText === '[DONE]') continue

                let event: StreamPayload
                try {
                  event = JSON.parse(payloadText)
                } catch {
                  continue
                }

                const eventType = event.type || 'text'
                const content = event.content

                switch (eventType) {
                  case 'status':
                  case 'thought_start':
                    assistantMessage.content = typeof content === 'string' ? content : assistantMessage.content
                    break
                  case 'thought':
                  case 'thought_chunk':
                    if (typeof content === 'string' && content.trim()) {
                      assistantMessage.content = assistantMessage.content
                        ? `${assistantMessage.content}\n${content}`
                        : content
                    }
                    break
                  case 'result': {
                    const personas = Array.isArray(content) ? content : content ? [content] : []
                    assistantMessage.personas = personas as Persona[]
                    assistantMessage.content = personas.length
                      ? `Generated ${personas.length} personas.`
                      : 'Generation complete.'
                    break
                  }
                  case 'error':
                    throw new Error(typeof content === 'string' ? content : 'Generation failed')
                  case 'count':
                  case 'progress':
                  case 'action':
                  case 'observation':
                    // Backward-compatible event types from older clients.
                    break
                  default:
                    if (typeof content === 'string' && content.trim()) {
                      assistantMessage.content = assistantMessage.content
                        ? `${assistantMessage.content}\n${content}`
                        : content
                    }
                }
              }
            }

            if (!assistantMessage.content) {
              assistantMessage.content = assistantMessage.personas?.length
                ? `Generated ${assistantMessage.personas.length} personas.`
                : 'Generation complete.'
            }

            message.success('Generation successful')
            return
          } catch (error) {
            lastError = error
            const assistantMessage = this.messages[this.messages.length - 1]
            if (assistantMessage && assistantMessage.role === 'assistant') {
              assistantMessage.content = error instanceof Error ? error.message : 'Generation failed'
            }

            if (retries === maxRetries) {
              message.error('Generation failed. Please try again later.')
              throw error
            }

            await sleep(1000)
          }
        }
      } finally {
        this.loading = false
      }

      if (lastError) {
        throw lastError
      }
    },
    clearHistory() {
      this.messages = []
    }
  }
})
