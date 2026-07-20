<template>
  <div class="persona-page">
    <div class="welcome-section fade-in-up">
      <div class="welcome-content">
        <div class="welcome-text">
          <h2 class="welcome-title">智能体工坊</h2>
          <p class="welcome-subtitle">管理您的智能体角色，定义个性与认知体系</p>
        </div>
        <div class="welcome-panel">
          <div class="insight-grid">
            <button
              class="insight-tile"
              :class="{ active: visibilityFilter === 'all' }"
              type="button"
              @click="setVisibilityFilter('all')"
            >
              <span>全部智能体</span>
              <strong>{{ personaStore.personas.length }}</strong>
            </button>
            <button
              class="insight-tile"
              :class="{ active: visibilityFilter === 'public' }"
              type="button"
              @click="setVisibilityFilter('public')"
            >
              <span>公开角色</span>
              <strong>{{ publicPersonaCount }}</strong>
            </button>
            <button
              class="insight-tile"
              :class="{ active: visibilityFilter === 'private' }"
              type="button"
              @click="setVisibilityFilter('private')"
            >
              <span>私有角色</span>
              <strong>{{ privatePersonaCount }}</strong>
            </button>
            <button class="insight-tile" type="button" @click="activeTab = 'list'">
              <span>技能关联</span>
              <strong>{{ uniqueSkillCount }}</strong>
            </button>
          </div>

          <div class="spotlight-card" v-if="featuredPersona">
            <div>
              <span class="spotlight-label">焦点智能体</span>
              <strong>{{ featuredPersona.name }}</strong>
              <p>{{ featuredPersona.title || featuredPersona.stance || '等待补充角色定位' }}</p>
            </div>
            <div class="spotlight-actions">
              <a-button size="small" ghost @click="rotateSpotlight">换一个</a-button>
              <a-button size="small" type="primary" @click="showDetails(featuredPersona)">查看详情</a-button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="persona-content-wrapper">
        <div class="page-header">
          <a-space>
            <a-button type="primary" ghost style="border-color: #3bb36b; color: #3bb36b;" @click="showRealGodModal" class="real-god-btn">
              <global-outlined /> 女娲（智能创建）
            </a-button>
            <a-button type="primary" style="background: #3bb36b; border: none;" @click="showModal()">
              <plus-outlined /> 创建智能体
            </a-button>
          </a-space>
        </div>

        <a-tabs v-model:activeKey="activeTab" class="persona-tabs">
          <a-tab-pane key="grid" tab="卡片视图">
            <a-spin :spinning="personaStore.loading">
              <div class="persona-grid-container">
                <div class="persona-grid">
                  <a-card
                    v-for="persona in paginatedPersonas"
                    :key="persona.id"
                    hoverable
                    class="persona-card"
                  >
                    <div class="card-header">
                      <div class="user-info">
                        <a-avatar :style="{ backgroundColor: getAvatarColor(persona.name) }" size="large">
                          <img v-if="getPersonaAvatarSrc(persona.avatar)" :src="getPersonaAvatarSrc(persona.avatar)" :alt="persona.name" />
                          <template v-else>{{ getAvatarInitial(persona.name, '智') }}</template>
                        </a-avatar>
                        <div class="name-title">
                          <div class="name" :title="persona.name">{{ persona.name }}</div>
                          <div class="title" :title="persona.title || '暂无头衔'">
                            {{ persona.title || '暂无头衔' }}
                          </div>
                        </div>
                      </div>
                      <div class="actions">
                        <a-dropdown placement="bottomRight" :trigger="['click']">
                          <a-button type="text" size="small">
                            <template #icon><more-outlined /></template>
                          </a-button>
                          <template #overlay>
                            <a-menu>
                              <a-menu-item key="view" @click="showDetails(persona)">
                                <eye-outlined /> 查看详情
                              </a-menu-item>
                              <a-menu-item key="edit" @click="showModal(persona)">
                                <edit-outlined /> 编辑
                              </a-menu-item>
                              <a-menu-item key="delete" @click="showDeleteConfirm(persona)">
                                <span style="color: #ff4d4f"><delete-outlined /> 删除</span>
                              </a-menu-item>
                            </a-menu>
                          </template>
                        </a-dropdown>
                      </div>
                    </div>

                    <div class="persona-content">
                      <p class="bio" :title="persona.bio">{{ persona.bio || '暂无简介' }}</p>
                      <div class="stance" v-if="persona.stance">
                        <span class="label">立场:</span> {{ persona.stance }}
                      </div>
                      <div class="tags">
                        <a-tag v-if="persona.is_public" color="green">公开</a-tag>
                        <a-tag v-else color="blue">私有</a-tag>
                        <a-tag v-for="tag in persona.theories.slice(0, 2)" :key="tag">{{ tag }}</a-tag>
                        <a-tag v-if="persona.theories.length > 2">...</a-tag>
                        <a-tag v-for="skill in persona.skills.slice(0, 2)" :key="skill" color="geekblue">{{ skill }}</a-tag>
                        <a-tag v-if="persona.skills.length > 2">+{{ persona.skills.length - 2 }}</a-tag>
                      </div>
                    </div>
                  </a-card>
                
                <!-- Empty State -->
                <div v-if="filteredPersonas.length === 0" class="empty-state">
                  <a-empty :description="personaStore.personas.length === 0 ? '暂无智能体，快去创建一个吧' : '当前筛选暂无智能体'" />
                </div>
              </div>
              
              <div class="pagination-wrapper" v-if="filteredPersonas.length > 0">
                <a-pagination
                  v-model:current="currentPage"
                  v-model:pageSize="pageSize"
                  :total="filteredPersonas.length"
                  :show-size-changer="false"
                  @change="onPageChange"
                  align="end"
                />
              </div>
            </div>
          </a-spin>
        </a-tab-pane>
        
        <a-tab-pane key="list" tab="列表视图">
          <a-table
            :columns="columns"
            :data-source="filteredPersonas"
            :loading="personaStore.loading"
            row-key="id"
            tableLayout="fixed"
            :scroll="{ x: 1000 }"
            size="middle"
            :pagination="{ pageSize: 6, showSizeChanger: false, align: 'end' }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'bio'">
                <a-tooltip :title="record.bio">
                  <div class="table-text-ellipsis">{{ record.bio }}</div>
                </a-tooltip>
              </template>
              <template v-if="column.key === 'stance'">
                <a-tooltip :title="record.stance">
                  <div class="table-text-ellipsis">{{ record.stance }}</div>
                </a-tooltip>
              </template>
              <template v-if="column.key === 'theories'">
                <div class="table-tags">
                  <a-tag v-for="tag in record.theories.slice(0, 2)" :key="tag">{{ tag }}</a-tag>
                  <a-popover v-if="record.theories.length > 2">
                    <template #content>
                      <a-tag v-for="tag in record.theories.slice(2)" :key="tag" style="margin-bottom: 4px;">{{ tag }}</a-tag>
                    </template>
                    <a-tag>+{{ record.theories.length - 2 }}</a-tag>
                  </a-popover>
                </div>
              </template>
              <template v-if="column.key === 'is_public'">
                <a-tag :color="record.is_public ? 'green' : 'blue'">
                  {{ record.is_public ? '公开' : '私有' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'action'">
                <a-space>
                  <a-button type="link" size="small" @click="showDetails(record)">详情</a-button>
                  <a-button type="link" size="small" @click="showModal(record)">编辑</a-button>
                  <a-button type="link" size="small" danger @click="showDeleteConfirm(record)">删除</a-button>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </div>

    <RealGodAgentModal
      v-model:open="realGodModalVisible"
    />

    <a-modal
      v-model:open="visible"
      :title="editingId ? '编辑智能体' : '创建智能体'"
      width="640px"
      :get-container="false"
      @ok="handleOk"
      :confirmLoading="submitting"
    >
      <a-form
        layout="vertical"
        ref="formRef"
        :model="formState"
        class="persona-form"
      >
        <a-divider orientation="left">基本信息</a-divider>
        <a-form-item label="头像">
          <div class="avatar-editor" data-test="persona-avatar-editor">
            <a-avatar :size="72" :style="{ backgroundColor: getAvatarColor(formState.name || '智能体') }" class="avatar-preview">
              <img v-if="formAvatarSrc" :src="formAvatarSrc" alt="智能体头像预览" />
              <template v-else>{{ getAvatarInitial(formState.name, '智') }}</template>
            </a-avatar>
            <div class="avatar-editor-body">
              <div class="avatar-editor-title">头像形象</div>
              <p>上传图片或让 AI 按名称生成；不设置时自动使用名称首字。</p>
              <div class="avatar-actions">
                <input
                  ref="avatarInputRef"
                  type="file"
                  accept="image/*"
                  class="avatar-file-input"
                  data-test="persona-avatar-file"
                  @change="handleAvatarFileChange"
                />
                <a-button size="small" :loading="avatarUploading" data-test="persona-avatar-upload" @click="triggerAvatarUpload">
                  上传头像
                </a-button>
                <a-button size="small" type="primary" ghost data-test="persona-avatar-generate" @click="generateAvatarForForm">
                  AI 生成头像
                </a-button>
                <a-button size="small" type="link" data-test="persona-avatar-clear" @click="clearAvatarForForm">
                  使用默认首字
                </a-button>
              </div>
            </div>
          </div>
        </a-form-item>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="名称" name="name" :rules="[{ required: true, message: '请输入名称' }]">
              <a-input v-model:value="formState.name" placeholder="例如：苏格拉底" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="头衔" name="title">
              <a-input v-model:value="formState.title" placeholder="例如：古希腊哲学家" />
            </a-form-item>
          </a-col>
        </a-row>
        
        <a-form-item label="简介" name="bio">
          <a-textarea v-model:value="formState.bio" :rows="3" placeholder="简要描述智能体的背景和生平" />
        </a-form-item>

        <a-divider orientation="left">认知体系</a-divider>
        
        <a-form-item label="理论标签 (用逗号分隔)" name="theories_str">
          <a-input v-model:value="formState.theories_str" placeholder="例如：精神助产术, 辩证法, 讽刺" />
        </a-form-item>
        
        <a-form-item label="核心立场" name="stance">
          <a-input v-model:value="formState.stance" placeholder="例如：追求真理，质疑一切" />
        </a-form-item>

        <a-form-item label="可用技能" name="skills">
          <a-select
            v-model:value="formState.skills"
            mode="multiple"
            :options="skillOptions"
            placeholder="选择这个智能体可以使用的技能"
            :maxTagCount="4"
          />
        </a-form-item>

        <a-form-item label="支持模态" name="modalities">
          <a-select
            v-model:value="formState.modalities"
            mode="multiple"
            :options="modalityOptions"
            placeholder="文本 / 图片 / 视频 / 音频 / 文件 / 成果物"
            :maxTagCount="4"
          />
        </a-form-item>

        <a-divider orientation="left">高级设置</a-divider>
        
        <a-form-item label="系统提示词 (System Prompt)" name="system_prompt">
          <a-textarea
            v-model:value="formState.system_prompt"
            :rows="4"
            placeholder="定义智能体在对话中的行为准则和指令"
          />
        </a-form-item>
        
        <a-form-item name="is_public">
          <a-checkbox v-model:checked="formState.is_public">
            设为公开智能体 (其他用户可见)
          </a-checkbox>
        </a-form-item>

      </a-form>
    </a-modal>

    <a-drawer
      v-model:open="detailsVisible"
      title="智能体详情"
      placement="right"
      width="min(920px, calc(100vw - 32px))"
      class="persona-detail-drawer"
    >
      <template v-if="currentPersona">
        <div class="persona-detail-panel">
          <div class="detail-avatar-strip">
            <a-avatar :size="76" :style="{ backgroundColor: getAvatarColor(currentPersona.name) }">
              <img v-if="getPersonaAvatarSrc(currentPersona.avatar)" :src="getPersonaAvatarSrc(currentPersona.avatar)" :alt="currentPersona.name" />
              <template v-else>{{ getAvatarInitial(currentPersona.name, '智') }}</template>
            </a-avatar>
            <div>
              <strong>{{ currentPersona.name }}</strong>
              <span>{{ currentPersona.title || '暂无头衔' }}</span>
            </div>
          </div>

          <div class="persona-detail-grid">
            <div class="persona-detail-card">
              <span>名称</span>
              <strong>{{ currentPersona.name }}</strong>
            </div>
            <div class="persona-detail-card">
              <span>头衔</span>
              <strong>{{ currentPersona.title }}</strong>
            </div>
            <div class="persona-detail-card persona-detail-card-wide">
              <span>核心立场</span>
              <strong>{{ currentPersona.stance }}</strong>
            </div>
          </div>

          <div class="persona-detail-chip-grid">
            <div class="persona-detail-section">
              <h3>理论标签</h3>
              <div class="persona-chip-row">
                <a-tag v-for="tag in currentPersona.theories" :key="tag">{{ tag }}</a-tag>
              </div>
            </div>
            <div class="persona-detail-section">
              <h3>技能</h3>
              <div class="persona-chip-row">
                <a-tag v-for="skill in currentPersona.skills" :key="skill" color="geekblue">{{ skill }}</a-tag>
              </div>
            </div>
            <div class="persona-detail-section">
              <h3>模态</h3>
              <div class="persona-chip-row">
                <a-tag v-for="mode in currentPersona.modalities" :key="mode" color="cyan">{{ mode }}</a-tag>
              </div>
            </div>
          </div>

          <div class="persona-detail-text-grid">
            <div class="persona-detail-section persona-text-section">
              <h3>简介</h3>
              <div class="persona-pre-wrap">{{ currentPersona.bio }}</div>
            </div>
            <div class="persona-detail-section persona-text-section">
              <h3>系统提示词</h3>
              <div class="persona-pre-wrap persona-system-prompt">
                {{ currentPersona.system_prompt }}
              </div>
            </div>
          </div>
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref, computed, createVNode, watch } from 'vue'
import { usePersonaStore, type Persona } from '@/stores/persona'
import { useAuthStore } from '@/stores/auth'
import { message, Modal } from 'ant-design-vue'
import request from '@/utils/request'
import RealGodAgentModal from '@/components/god/RealGodAgentModal.vue'
import { generatePersonaAvatar, getAvatarInitial, isImageAvatar } from '@/utils/avatar'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  GlobalOutlined,
  MoreOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons-vue'

const personaStore = usePersonaStore()
const authStore = useAuthStore()
const visible = ref(false)
const detailsVisible = ref(false)
const realGodModalVisible = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const activeTab = ref('grid')
const currentPersona = ref<Persona | null>(null)
const skillOptions = ref<Array<{ label: string; value: string }>>([])
const visibilityFilter = ref<'all' | 'public' | 'private'>('all')
const spotlightIndex = ref(0)
const avatarInputRef = ref<HTMLInputElement | null>(null)
const avatarUploading = ref(false)
const modalityOptions = [
  { label: '文本', value: 'text' },
  { label: '图片', value: 'image' },
  { label: '视频', value: 'video' },
  { label: '音频', value: 'audio' },
  { label: '文件', value: 'file' },
  { label: '成果物', value: 'artifact' }
]


// Pagination
const currentPage = ref(1)
const pageSize = ref(6)

const publicPersonaCount = computed(() => personaStore.personas.filter(persona => persona.is_public).length)
const privatePersonaCount = computed(() => personaStore.personas.length - publicPersonaCount.value)
const uniqueSkillCount = computed(() => {
  const skills = new Set<string>()
  personaStore.personas.forEach(persona => {
    ;(persona.skills || []).forEach(skill => skills.add(skill))
  })
  return skills.size
})

const filteredPersonas = computed(() => {
  if (visibilityFilter.value === 'public') {
    return personaStore.personas.filter(persona => persona.is_public)
  }

  if (visibilityFilter.value === 'private') {
    return personaStore.personas.filter(persona => !persona.is_public)
  }

  return personaStore.personas
})

const featuredPersona = computed(() => {
  if (!filteredPersonas.value.length) return null
  return filteredPersonas.value[spotlightIndex.value % filteredPersonas.value.length]
})

const paginatedPersonas = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredPersonas.value.slice(start, end)
})

const onPageChange = (page: number) => {
  currentPage.value = page
}

const setVisibilityFilter = (filter: 'all' | 'public' | 'private') => {
  visibilityFilter.value = filter
  currentPage.value = 1
  spotlightIndex.value = 0
}

const rotateSpotlight = () => {
  if (!filteredPersonas.value.length) return
  spotlightIndex.value = (spotlightIndex.value + 1) % filteredPersonas.value.length
}

watch(
  () => filteredPersonas.value.length,
  (total) => {
    const maxPage = Math.max(1, Math.ceil(total / pageSize.value))
    if (currentPage.value > maxPage) {
      currentPage.value = maxPage
    }
    if (spotlightIndex.value >= total) {
      spotlightIndex.value = 0
    }
  }
)

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 120 },
  { title: '头衔', dataIndex: 'title', key: 'title', width: 120 },
  { title: '简介', dataIndex: 'bio', key: 'bio', ellipsis: true, width: 200 },
  { title: '核心立场', dataIndex: 'stance', key: 'stance', width: 150 },
  { title: '理论标签', dataIndex: 'theories', key: 'theories', width: 200 },
  { title: '可见性', dataIndex: 'is_public', key: 'is_public', width: 80 },
  { title: '操作', key: 'action', width: 180 }
]

const formState = reactive({
  name: '',
  title: '',
  bio: '',
  theories_str: '',
  stance: '',
  system_prompt: '',
  is_public: false,
  avatar: '',
  skills: [] as string[],
  modalities: ['text'] as string[]
})

const formAvatarSrc = computed(() => getPersonaAvatarSrc(formState.avatar))

const getPersonaAvatarSrc = (avatar?: string) => {
  return isImageAvatar(avatar) ? avatar : ''
}

const fetchSkillCatalog = async () => {
  try {
    const res = await request.get('/skills/catalog')
    skillOptions.value = (res.data || []).map((skill: any) => ({
      label: `${skill.name} · ${skill.skill_key}`,
      value: skill.skill_key
    }))
  } catch (error) {
    console.error('Failed to fetch skill catalog:', error)
  }
}

onMounted(async () => {
  await Promise.all([
    personaStore.fetchPersonas(),
    fetchSkillCatalog(),
  ])
})

const getAvatarColor = (name: string) => {
  const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#3bb36b', '#52c41a', '#eb2f96']
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  const index = Math.abs(hash) % colors.length
  return colors[index]
}

const showModal = (record?: Persona) => {
  visible.value = true
  if (record) {
    editingId.value = record.id
    Object.assign(formState, {
      ...record,
      theories_str: record.theories.join(', '),
      skills: [...(record.skills || ['chat.reply'])],
      modalities: [...(record.modalities || ['text'])]
    })
  } else {
    editingId.value = null
    Object.assign(formState, {
      name: '',
      title: '',
      bio: '',
      theories_str: '',
      stance: '',
      system_prompt: '',
      is_public: false,
      avatar: '',
      skills: ['chat.reply'],
      modalities: ['text']
    })
  }
}

const triggerAvatarUpload = () => {
  avatarInputRef.value?.click()
}

const handleAvatarFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const formData = new FormData()
  formData.append('file', file)
  avatarUploading.value = true

  try {
    const res = await request.post('/upload/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    formState.avatar = res.data?.preview_url || res.data?.storage_url || ''
    message.success('头像已上传')
  } catch (error) {
    console.error('Failed to upload persona avatar:', error)
    message.error('头像上传失败，请稍后重试')
  } finally {
    avatarUploading.value = false
    input.value = ''
  }
}

const generateAvatarForForm = () => {
  formState.avatar = generatePersonaAvatar(formState.name || '智能体', formState.title, formState.stance)
  message.success('已生成头像')
}

const clearAvatarForForm = () => {
  formState.avatar = ''
}

const handleOk = async () => {
  if (!formState.name) {
    message.warning('请输入智能体名称')
    return
  }

  submitting.value = true
  const data = {
    ...formState,
    theories: formState.theories_str.split(/[,，]/).map(s => s.trim()).filter(s => s),
    skills: formState.skills.length > 0 ? formState.skills : ['chat.reply'],
    modalities: formState.modalities.length > 0 ? formState.modalities : ['text'],
    capabilities_version: 1
  }
  
  try {
    if (editingId.value) {
      await personaStore.updatePersona(editingId.value, data)
      message.success('更新成功')
    } else {
      await personaStore.createPersona(data)
      message.success('创建成功')
    }
    visible.value = false
  } catch (e: unknown) {
    if (e instanceof Error) {
        message.error(e.message || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (id: number) => {
  try {
    await personaStore.deletePersona(id)
    message.success('删除成功')
  } catch (e) {
    message.error('删除失败')
  }
}

const showDeleteConfirm = (persona: Persona) => {
  Modal.confirm({
    title: '确定要删除这个智能体吗？',
    icon: createVNode(ExclamationCircleOutlined),
    content: `删除后无法恢复：${persona.name}`,
    okText: '确认删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      await handleDelete(persona.id)
    }
  })
}

const showDetails = (persona: Persona) => {
  currentPersona.value = persona
  detailsVisible.value = true
}

const showRealGodModal = () => {
    realGodModalVisible.value = true
}
</script>

<style scoped>
.persona-page {
  max-width: 1280px;
  margin: 0 auto;
  padding: 24px;
  min-height: 100vh;
}

.welcome-section {
  margin-bottom: 28px;
}

.welcome-content {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(420px, 0.9fr);
  align-items: center;
  gap: 28px;
  background: #3bb36b;
  border-radius: 18px;
  padding: 30px 34px;
  box-shadow: 0 18px 44px rgba(59, 179, 107, 0.22);
  position: relative;
  overflow: hidden;
}

.welcome-content::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    linear-gradient(120deg, rgba(255, 255, 255, 0.14), transparent 34%),
    repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.08) 0 1px, transparent 1px 58px);
  pointer-events: none;
}

.welcome-text {
  color: white;
  position: relative;
  z-index: 1;
}

.welcome-title {
  font-size: 30px;
  font-weight: 800;
  margin: 0 0 8px;
  color: white;
  letter-spacing: 0;
}

.welcome-subtitle {
  font-size: 15px;
  margin: 0;
  color: rgba(255, 255, 255, 0.9);
}

.welcome-panel {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(220px, 1.05fr);
  gap: 12px;
  position: relative;
  z-index: 1;
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.insight-tile {
  border: 1px solid rgba(255, 255, 255, 0.28);
  background: rgba(255, 255, 255, 0.13);
  color: #ffffff;
  border-radius: 8px;
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}

.insight-tile:hover,
.insight-tile.active {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.24);
  border-color: rgba(255, 255, 255, 0.65);
}

.insight-tile span {
  display: block;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.82);
  line-height: 1.2;
}

.insight-tile strong {
  display: block;
  margin-top: 5px;
  font-size: 22px;
  line-height: 1;
  color: #ffffff;
}

.spotlight-card {
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid rgba(255, 255, 255, 0.32);
  background: rgba(18, 79, 47, 0.23);
  border-radius: 8px;
  padding: 14px;
  color: #ffffff;
}

.spotlight-label {
  display: block;
  margin-bottom: 6px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  font-weight: 700;
}

.spotlight-card strong {
  display: block;
  font-size: 17px;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.spotlight-card p {
  margin: 6px 0 0;
  color: rgba(255, 255, 255, 0.78);
  font-size: 12px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.spotlight-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.spotlight-actions :deep(.ant-btn) {
  border-radius: 8px;
}

.spotlight-actions :deep(.ant-btn-background-ghost) {
  color: #ffffff;
  border-color: rgba(255, 255, 255, 0.58);
}

.spotlight-actions :deep(.ant-btn-primary) {
  background: #ffffff;
  border-color: #ffffff;
  color: #24834f;
  font-weight: 700;
}

.persona-content-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0;
}

.avatar-editor {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 14px;
  align-items: center;
  border: 1px solid #e6eee8;
  border-radius: 12px;
  background: #f8fbf8;
  padding: 14px;
}

.avatar-preview {
  flex-shrink: 0;
  box-shadow: 0 12px 22px rgba(59, 179, 107, 0.18);
}

.avatar-preview :deep(img),
.user-info :deep(.ant-avatar img),
.detail-avatar-strip :deep(.ant-avatar img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-editor-body {
  min-width: 0;
}

.avatar-editor-title {
  color: #141816;
  font-size: 14px;
  font-weight: 800;
}

.avatar-editor-body p {
  margin: 4px 0 10px;
  color: #738078;
  font-size: 12px;
  line-height: 1.5;
}

.avatar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.avatar-file-input {
  display: none;
}

.persona-detail-drawer :deep(.ant-drawer-body) {
  height: calc(100vh - 56px);
  padding: 18px;
  overflow: hidden;
}

.persona-detail-panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-avatar-strip {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px;
  border: 1px solid #e6eee8;
  border-radius: 14px;
  background: #f8fbf8;
  flex: 0 0 auto;
}

.detail-avatar-strip strong,
.detail-avatar-strip span {
  display: block;
}

.detail-avatar-strip strong {
  color: #141816;
  font-size: 18px;
  line-height: 1.3;
}

.detail-avatar-strip span {
  margin-top: 4px;
  color: #738078;
  font-size: 13px;
}

.persona-detail-grid,
.persona-detail-chip-grid,
.persona-detail-text-grid {
  display: grid;
  gap: 12px;
}

.persona-detail-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  flex: 0 0 auto;
}

.persona-detail-card,
.persona-detail-section {
  min-width: 0;
  border: 1px solid #e5ece7;
  border-radius: 12px;
  background: #ffffff;
}

.persona-detail-card {
  padding: 12px;
}

.persona-detail-card-wide {
  grid-column: 1 / -1;
}

.persona-detail-card span,
.persona-detail-section h3 {
  color: #738078;
  font-size: 12px;
  font-weight: 800;
}

.persona-detail-card span {
  display: block;
  margin-bottom: 6px;
}

.persona-detail-card strong {
  display: block;
  color: #141816;
  font-size: 14px;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.persona-detail-chip-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  flex: 0 0 auto;
}

.persona-detail-section {
  padding: 12px;
}

.persona-detail-section h3 {
  margin: 0 0 10px;
}

.persona-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.persona-detail-text-grid {
  min-height: 0;
  grid-template-columns: minmax(0, 0.42fr) minmax(0, 1fr);
  flex: 1 1 auto;
}

.persona-text-section {
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.persona-pre-wrap {
  min-height: 0;
  flex: 1;
  overflow: auto;
  white-space: pre-wrap;
  color: #1a1d1e;
  line-height: 1.7;
  background: #f8faf8;
  border-radius: 8px;
  padding: 12px;
}

.persona-system-prompt {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', monospace;
  font-size: 13px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.persona-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  grid-auto-rows: minmax(238px, auto);
  gap: 16px;
  padding-bottom: 0;
}

.persona-grid-container {
  min-height: 600px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pagination-wrapper {
  margin-top: auto;
  padding-top: 0;
  width: 100%;
  flex-shrink: 0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.persona-card {
  min-height: 238px;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-color: #edf3ee;
}

.persona-card :deep(.ant-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  overflow: hidden;
}

.persona-card:hover {
  transform: translateY(-5px);
  border-color: #b8dfc7;
  box-shadow: 0 16px 34px rgba(29, 73, 47, 0.12);
}



.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.name-title {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.name {
  font-size: 16px;
  font-weight: 500;
  color: rgba(0,0,0,0.85);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.title {
  font-size: 12px;
  color: rgba(0,0,0,0.45);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.actions {
  flex-shrink: 0;
  margin-left: 8px;
}

.persona-content {
  margin-top: 0;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.bio {
  color: rgba(0,0,0,0.45);
  font-size: 13px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  margin-bottom: 8px;
  min-height: 0;
  line-height: 1.6;
}

.stance {
  font-size: 13px;
  color: rgba(0,0,0,0.65);
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  flex-shrink: 0;
  line-height: 1.55;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-height: 56px;
  overflow: hidden;
  flex-shrink: 0;
}

.tags :deep(.ant-tag) {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: top;
}

.empty-state {
  grid-column: 1 / -1;
  padding: 48px 0;
  text-align: center;
}

.table-text-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 100%;
  width: 100%;
  display: block;
}

.table-tags {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  overflow: hidden;
}

.table-tags :deep(.ant-tag) {
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: top;
}

@media (max-width: 1100px) {
  .welcome-content,
  .welcome-panel {
    grid-template-columns: 1fr;
  }

  .persona-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .persona-page {
    padding: 16px;
  }

  .welcome-content {
    padding: 24px;
  }

  .insight-grid,
  .persona-grid {
    grid-template-columns: 1fr;
  }

  .page-header :deep(.ant-space) {
    width: 100%;
    align-items: stretch;
  }

  .page-header :deep(.ant-space-item),
  .page-header :deep(.ant-btn) {
    width: 100%;
  }

  .pagination-wrapper {
    justify-content: center;
  }

  .persona-detail-drawer :deep(.ant-drawer-body) {
    height: auto;
    max-height: calc(100vh - 56px);
    overflow: auto;
  }

  .persona-detail-grid,
  .persona-detail-chip-grid,
  .persona-detail-text-grid {
    grid-template-columns: 1fr;
  }

  .persona-pre-wrap {
    max-height: 280px;
  }
}
</style>
