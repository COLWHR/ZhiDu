<template>
  <div class="time-gate-page">
    <a-layout class="chat-layout">
      <!-- 左侧智能体列表 -->
      <a-layout-sider width="280" class="sider-section">
        <div class="sider-header">
          <h3 class="sider-title">我的智能体</h3>
          <a-button type="primary" size="small" ghost @click="handleAddAgent">
            <plus-outlined /> 添加
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
      
      <!-- 右侧对话区域 -->
      <a-layout class="chat-section">
        <div v-if="!currentAgent" class="chat-welcome">
          <div class="welcome-avatar">⏳</div>
          <h2>欢迎来到时空之门</h2>
          <p>选择左侧的智能体，开启跨时空对话</p>
        </div>
        
        <div v-else class="chat-container">
          <!-- 对话头部 -->
          <div class="chat-header">
            <div class="current-agent-info">
              <a-avatar size="small" :style="{ background: getAvatarGradient(currentAgent.name) }">
                {{ currentAgent.name[0] }}
              </a-avatar>
              <span class="agent-name">{{ currentAgent.name }}</span>
              <span class="agent-title">{{ currentAgent.title }}</span>
            </div>
            <div class="header-actions">
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
              <span class="tip-text">支持粘贴图片（Ctrl+V）直接发送</span>
            </div>
            <a-textarea
              v-model:value="inputMessage"
              :rows="3"
              placeholder="请输入消息，按Enter发送，Shift+Enter换行，支持粘贴/上传图片"
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
import { ref, onMounted, nextTick, computed } from 'vue';
import { usePersonaStore } from '@/stores/persona';
import { useAuthStore } from '@/stores/auth';
import { 
  PlusOutlined, 
  MoreOutlined, 
  SendOutlined, 
  DeleteOutlined,
  PictureOutlined
} from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';
import request from '@/utils/request';
import { marked } from 'marked';

const personaStore = usePersonaStore();
const authStore = useAuthStore();

// 状态
const currentAgent = ref<any>(null);
const messages = ref<Array<{ role: 'user' | 'assistant', content: string, timestamp: number }>>([]);
const inputMessage = ref('');
const loading = ref(false);
const uploadingImage = ref(false);
const messagesContainer = ref<HTMLElement | null>(null);
const imageInput = ref<HTMLInputElement | null>(null);

// 计算属性
const getAvatarGradient = (name: string) => {
  const colors = [
    '#667eea', '#764ba2', '#f093fb', '#4facfe',
    '#43e97b', '#fa709a', '#fee140', '#30cfd0'
  ];
  const index = name.charCodeAt(0) % colors.length;
  return colors[index];
};

// 方法
const handleAddAgent = () => {
  message.info('请先去智能体工坊创建智能体');
};

const switchAgent = async (agent: any) => {
  currentAgent.value = agent;
  messages.value = [];
  loading.value = true;
  
  try {
    // 加载历史对话
    const res = await request.get(`/agents/chat/history/${agent.id}`);
    if (res.data && res.data.length > 0) {
      messages.value = res.data;
    } else {
      // 没有历史记录，显示欢迎消息
      messages.value.push({
        role: 'assistant',
        content: `你好，我是${agent.name}。${agent.bio || '很高兴能和你交流！'}`,
        timestamp: Date.now()
      });
    }
  } catch (error) {
    console.error('加载历史对话失败:', error);
    // 加载失败也显示欢迎消息
    messages.value.push({
      role: 'assistant',
      content: `你好，我是${agent.name}。${agent.bio || '很高兴能和你交流！'}`,
      timestamp: Date.now()
    });
  } finally {
    loading.value = false;
    await nextTick();
    scrollToBottom();
  }
};

const handleSend = async (e?: KeyboardEvent) => {
  if (e && e.shiftKey) return;
  e?.preventDefault();
  
  if (!currentAgent.value) {
    message.warning('请先选择一个智能体');
    return;
  }
  
  const content = inputMessage.value.trim();
  if (!content) return;
  
  // 添加用户消息
  messages.value.push({
    role: 'user',
    content,
    timestamp: Date.now()
  });
  inputMessage.value = '';
  loading.value = true;
  
  // 添加空的助手回复，用于流式填充
  const assistantMsgIndex = messages.value.length;
  messages.value.push({
    role: 'assistant',
    content: '',
    timestamp: Date.now()
  });
  
  await nextTick();
  scrollToBottom();
  
  try {
    // 保存用户消息
    await request.post('/agents/chat/message', {
      persona_id: currentAgent.value.id,
      role: 'user',
      content: content
    });
    
    // 构造历史消息（排除刚添加的空助手消息）
    const contextMessages = messages.value.slice(0, -1).map(msg => ({
      speaker: msg.role === 'user' ? '用户' : currentAgent.value.name,
      content: msg.content
    }));
    
    // 调用流式对话API
    const response = await fetch('/api/v1/agents/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify({
        agent_name: currentAgent.value.name,
        persona_json: currentAgent.value,
        context_messages: contextMessages,
        theme: '自由对话'
      })
    });
    
    if (!response.ok) {
      throw new Error('网络请求失败');
    }
    
    const reader = response.body?.getReader();
    const decoder = new TextDecoder('utf-8');
    
    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n').filter(line => line.trim() !== '');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') continue;
            
            try {
              const parsed = JSON.parse(data);
              if (parsed.content) {
                messages.value[assistantMsgIndex].content += parsed.content;
                await nextTick();
                scrollToBottom();
              } else if (parsed.error) {
                throw new Error(parsed.error);
              }
            } catch (e) {
              console.error('解析响应失败:', e);
            }
          }
        }
      }
    }
    
    // 如果内容为空，显示默认提示
    if (!messages.value[assistantMsgIndex].content.trim()) {
      messages.value[assistantMsgIndex].content = '抱歉，我暂时无法回答这个问题。';
    }
    
    // 保存助手回复
    await request.post('/agents/chat/message', {
      persona_id: currentAgent.value.id,
      role: 'assistant',
      content: messages.value[assistantMsgIndex].content
    });
    
  } catch (error) {
    console.error('对话失败:', error);
    message.error('对话失败，请稍后重试');
    messages.value[assistantMsgIndex].content = '抱歉，我遇到了一些问题，暂时无法回答你的问题。';
    
    // 保存错误回复
    await request.post('/agents/chat/message', {
      persona_id: currentAgent.value.id,
      role: 'assistant',
      content: messages.value[assistantMsgIndex].content
    });
  } finally {
    loading.value = false;
    await nextTick();
    scrollToBottom();
  }
};

const clearChat = async () => {
  if (!currentAgent.value) return;
  
  try {
    await request.delete(`/agents/chat/history/${currentAgent.value.id}`);
    messages.value = [];
    messages.value.push({
      role: 'assistant',
      content: `你好，我是${currentAgent.value.name}。${currentAgent.value.bio || '很高兴能和你交流！'}`,
      timestamp: Date.now()
    });
    message.success('对话历史已清空');
  } catch (error) {
    console.error('清空对话失败:', error);
    message.error('清空对话失败，请稍后重试');
  }
};

const formatMessage = (content: string) => {
  return marked.parse(content);
};

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp);
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`;
};

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

// 图片上传相关
const triggerImageUpload = () => {
  imageInput.value?.click();
};

const handleImageUpload = async (e: Event) => {
  const target = e.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;
  
  await uploadAndInsertImage(file);
  target.value = ''; // 重置input，允许重复选择同一文件
};

const handlePaste = async (e: ClipboardEvent) => {
  const items = e.clipboardData?.items;
  if (!items) return;
  
  for (const item of items) {
    if (item.type.indexOf('image') !== -1) {
      e.preventDefault();
      const file = item.getAsFile();
      if (file) {
        await uploadAndInsertImage(file);
      }
      break;
    }
  }
};

const uploadAndInsertImage = async (file: File) => {
  if (!file.type.startsWith('image/')) {
    message.error('请选择图片文件');
    return;
  }
  
  // 限制图片大小为10MB
  if (file.size > 10 * 1024 * 1024) {
    message.error('图片大小不能超过10MB');
    return;
  }
  
  uploadingImage.value = true;
  
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const res = await request.post('/upload/image', formData);
    
    if (res.data && res.data.url) {
      const imageMarkdown = `![image](${res.data.url})\n`;
      inputMessage.value += imageMarkdown;
      message.success('图片上传成功');
    } else {
      throw new Error('上传失败，未返回图片URL');
    }
  } catch (error) {
    console.error('图片上传失败:', error);
    message.error('图片上传失败，请稍后重试');
  } finally {
    uploadingImage.value = false;
  }
};

onMounted(() => {
  personaStore.fetchPersonas(authStore.user?.id);
});
</script>

<style scoped>
.time-gate-page {
  height: 100vh;
  background: #f5f7fa;
  overflow: hidden;
}

.chat-layout {
  height: 100%;
}

.sider-section {
  background: white;
  border-right: 1px solid #f0f0f0;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.05);
}

.sider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.sider-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: #1a1a2e;
}

.agent-list {
  padding: 8px;
  height: calc(100vh - 74px);
  overflow-y: auto;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 4px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.agent-item:hover {
  background: #f5f3ff;
}

.agent-item.active {
  background: linear-gradient(135deg, #a6e3e9 0%, #71c9ce 100%);
  color: white;
}

.agent-info {
  flex: 1;
  overflow: hidden;
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
  background: #f5f7fa;
}

.chat-welcome {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #888;
}

.welcome-avatar {
  font-size: 64px;
  margin-bottom: 20px;
}

.chat-welcome h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #1a1a2e;
}

.chat-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #f0f0f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.current-agent-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.current-agent-info .agent-name {
  font-weight: 600;
  color: #1a1a2e;
}

.current-agent-info .agent-title {
  font-size: 13px;
  color: #888;
  margin-left: 8px;
}

.messages-container {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background: #f5f7fa;
}

.message-item {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
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
  padding: 12px 16px;
  border-radius: 16px;
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  line-height: 1.6;
  word-break: break-word;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message-item.user .message-bubble code,
.message-item.user .message-bubble pre {
  background: rgba(255, 255, 255, 0.2);
}

.message-time {
  font-size: 12px;
  color: #888;
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
  padding: 16px 24px;
  background: white;
  border-top: 1px solid #f0f0f0;
}

.input-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f5f5f5;
}

.tip-text {
  font-size: 12px;
  color: #999;
}

.chat-input {
  border-radius: 12px;
  margin-bottom: 12px;
}

.input-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
