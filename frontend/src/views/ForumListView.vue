<template>
  <div class="forum-list-page">
    <div class="page-header fade-in-up">
      <div class="header-content">
        <div class="header-icon">💬</div>
        <div class="header-title">
          <span class="title">圆桌论坛</span>
          <span class="subtitle">创建多智能体讨论组，观察思维碰撞的火花 ✨</span>
        </div>
      </div>
      <a-button type="primary" size="large" @click="showModal()" class="create-btn">
        <plus-outlined class="btn-icon" />
        <span>发起新讨论</span>
      </a-button>
    </div>

    <div class="forum-content fade-in-up" style="animation-delay: 0.1s;">
      <a-spin :spinning="forumStore.loading && forumStore.forums.length === 0">
        <div v-if="forumStore.loading && forumStore.forums.length === 0" class="forum-grid">
          <a-card v-for="i in 6" :key="i" class="forum-card glass-card">
            <a-skeleton active :paragraph="{ rows: 2 }" />
          </a-card>
        </div>
        <div v-else class="forum-grid">
          <a-card
            v-for="item in forumStore.forums"
            :key="item.id"
            hoverable
            class="forum-card glass-card"
            @click="$router.push(`/forums/${item.id}`)"
          >
            <a-card-meta>
              <template #title>
                <div class="card-title">
                  <span class="topic">{{ item.topic }}</span>
                  <a-tag :color="getStatusColor(item.status)" class="status-tag">
                    {{ getStatusText(item.status) }}
                  </a-tag>
                </div>
              </template>
              <template #description>
                <div class="card-desc">
                  <span class="desc-item">
                    <clock-circle-outlined />
                    {{ formatDate(item.start_time) }}
                  </span>
                  <span class="desc-item">
                    <user-outlined />
                    {{ (item as any).participant_count || 0 }} 位参与者
                  </span>
                </div>
              </template>
              <template #avatar>
                <a-avatar
                  shape="square"
                  size="large"
                  :style="{ background: getAvatarGradient(item.topic) }"
                  class="card-avatar"
                >
                  {{ item.topic[0] }}
                </a-avatar>
              </template>
            </a-card-meta>
            
            <div class="card-footer" @click.stop>
              <div class="footer-content">
                <a-popconfirm 
                  title="确定删除该论坛吗？" 
                  ok-text="确定"
                  cancel-text="取消"
                  @confirm="handleDelete(item.id)"
                  @click.stop
                >
                  <a-button type="text" danger size="small" class="delete-btn" @click.stop>
                    <delete-outlined /> 删除
                  </a-button>
                </a-popconfirm>
                <span class="action-text" @click="$router.push(`/forums/${item.id}`)">
                  进入讨论 <arrow-right-outlined class="arrow-icon" />
                </span>
              </div>
            </div>
          </a-card>
          
          <div v-if="forumStore.forums.length === 0 && !forumStore.loading" class="empty-state">
            <div class="empty-content">
              <div class="empty-icon">🎯</div>
              <p class="empty-text">暂无正在进行的论坛</p>
              <p class="empty-subtext">发起一个新的话题，让智能体们开始精彩的讨论吧！</p>
              <a-button type="primary" size="large" @click="showModal()" class="empty-create-btn">
                <plus-outlined /> 发起第一个讨论
              </a-button>
            </div>
          </div>
        </div>
      </a-spin>
    </div>

    <a-modal
      v-model:open="visible"
      title="发起新讨论"
      @ok="handleOk"
      :confirmLoading="submitting"
      width="560px"
      :footer="null"
      class="create-modal"
    >
      <div class="modal-content">
        <a-form layout="vertical" ref="formRef" :model="formState" class="create-form">
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
              <template #option="{ label }">
                 <div class="select-option">
                   <span class="option-avatar">{{ label[0] }}</span>
                   <span>{{ label }}</span>
                 </div>
              </template>
            </a-select>
            <div class="form-hint">
              💡 提示：您可以选择自己创建的智能体，也可以邀请公开的智能体加入。
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
            <a-button size="large" @click="visible = false" class="cancel-btn">
              取消
            </a-button>
            <a-button type="primary" size="large" @click="handleOk" :loading="submitting" class="confirm-btn">
              发起讨论
            </a-button>
          </div>
        </a-form>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed, watch } from 'vue'
import { useForumStore } from '@/stores/forum'
import { usePersonaStore } from '@/stores/persona'
import { useAuthStore } from '@/stores/auth'
import { message } from 'ant-design-vue'
import request from '@/utils/request'
import { PlusOutlined, ArrowRightOutlined, DeleteOutlined, ClockCircleOutlined, UserOutlined } from '@ant-design/icons-vue'

const forumStore = useForumStore()
const personaStore = usePersonaStore()
const authStore = useAuthStore()
const visible = ref(false)
const submitting = ref(false)
const formRef = ref()

const formState = reactive({
  topic: '',
  participant_ids: [] as number[],
  moderator_id: undefined as number | undefined,
  duration: 5
})

onMounted(() => {
  forumStore.fetchForums()
  forumStore.fetchModerators()
  personaStore.fetchPersonas()
})

const moderatorOptions = computed(() => {
  return forumStore.moderators.map(m => ({
    label: m.name,
    value: m.id
  }))
})

const personaOptions = computed(() => {
  return personaStore.personas.map(p => ({
    label: p.name,
    value: p.id
  }))
})

const getStatusColor = (status: string) => {
  switch (status) {
    case 'running': return 'processing'
    case 'pending': return 'warning'
    case 'closed':
    case 'finished': return 'default'
    case 'active': return 'processing'
    default: return 'default'
  }
}

const getStatusText = (status: string) => {
  switch (status) {
    case 'running': return '🔥 进行中'
    case 'pending': return '⏳ 未开始'
    case 'closed':
    case 'finished': return '✅ 已结束'
    case 'active': return '🔥 进行中'
    default: return '未知'
  }
}

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

const showModal = async () => {
  visible.value = true
  forumStore.fetchModerators()
  personaStore.fetchPersonas()
  
  formState.topic = ''
  formState.participant_ids = []
  formState.moderator_id = undefined
  formState.duration = 5
}

const handleOk = async () => {
  if (!formState.topic || formState.participant_ids.length === 0) {
    message.warning('请填写完整信息')
    return
  }
  
  submitting.value = true
  try {
    await forumStore.fetchModerators()
    if (formState.moderator_id && !forumStore.moderators.some(m => m.id === formState.moderator_id)) {
      formState.moderator_id = undefined
      message.warning('所选主持人已失效，请重新选择')
      return
    }
    await forumStore.createForum(formState.topic, formState.participant_ids, formState.duration, formState.moderator_id)
    visible.value = false
    message.success('讨论发起成功！🎉')
  } catch (e: unknown) {
    if (e instanceof Error) {
        message.error(e.message || '创建失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (id: number) => {
    try {
        await forumStore.deleteForum(id)
        message.success('删除成功')
    } catch (e: any) {
        console.error(e)
        message.error(e.message || '删除失败')
    }
}
</script>

<style scoped>
.forum-list-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px;
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  flex-wrap: wrap;
  gap: 20px;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  font-size: 40px;
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(-225deg, #69EACB 0%, #EACCF8 48%, #6654F1 100%);
  border-radius: 16px;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
}

.header-title {
  display: flex;
  flex-direction: column;
}

.title {
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1.2;
}

.subtitle {
  font-size: 14px;
  color: #888;
  margin-top: 4px;
}

.create-btn {
  height: 48px;
  padding: 0 24px;
  border-radius: 12px;
  font-weight: 600;
  font-size: 15px;
  background: linear-gradient(-225deg, #69EACB 0%, #EACCF8 48%, #6654F1 100%);
  border: none;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s ease;
}

.create-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-icon {
  font-size: 18px;
}

.forum-content {
  margin-top: 8px;
}

.forum-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.forum-card {
  border-radius: 16px;
  transition: all 0.3s ease;
  cursor: pointer;
  overflow: hidden;
}

.forum-card:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 40px rgba(102, 126, 234, 0.2);
}

.card-avatar {
  border-radius: 12px;
  color: white;
  font-weight: 600;
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.card-title .topic {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 600;
  font-size: 16px;
  color: #1a1a2e;
}

.status-tag {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 500;
}

.card-desc {
  margin-top: 12px;
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.desc-item {
  font-size: 13px;
  color: #888;
  display: flex;
  align-items: center;
  gap: 4px;
}

.card-footer {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.footer-content {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.delete-btn {
  color: #ff4d4f;
}

.action-text {
  color: #667eea;
  font-weight: 500;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 4px;
  transition: all 0.3s ease;
}

.action-text:hover {
  color: #764ba2;
}

.arrow-icon {
  transition: transform 0.3s ease;
}

.action-text:hover .arrow-icon {
  transform: translateX(4px);
}

.empty-state {
  grid-column: 1 / -1;
  padding: 60px 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-content {
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 8px;
}

.empty-subtext {
  font-size: 14px;
  color: #888;
  margin: 0 0 24px;
}

.empty-create-btn {
  height: 46px;
  padding: 0 28px;
  border-radius: 12px;
  font-weight: 600;
  background: linear-gradient(135deg, #a6e3e9 0%, #71c9ce 100%);
  border: none;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
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
  color: #1a1a2e;
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
  color: #667eea;
  font-size: 13px;
  background: #f5f3ff;
  padding: 10px 14px;
  border-radius: 8px;
  line-height: 1.5;
}

.cost-tip {
  margin-top: 8px;
  margin-bottom: 16px;
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
  background: linear-gradient(135deg, #a6e3e9 0%, #71c9ce 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
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
  background: #f0f2f5;
  border: none;
  color: #1a1a2e;
}

.confirm-btn {
  height: 44px;
  border-radius: 10px;
  padding: 0 28px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

@media (max-width: 768px) {
  .forum-list-page {
    padding: 16px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .title {
    font-size: 24px;
  }
  
  .header-icon {
    width: 56px;
    height: 56px;
    font-size: 32px;
  }
  
  .forum-grid {
    grid-template-columns: 1fr;
  }
}
</style>
