<template>
  <div class="skill-repository-view">
    <section class="page-band">
      <div>
        <h1>Skill 仓库</h1>
        <p>同步并浏览来自 SkillHub 的全局技能，供智能体能力配置使用。</p>
      </div>
      <a-button type="primary" :loading="store.syncing" @click="handleSync">
        <template #icon><cloud-sync-outlined /></template>
        同步 SkillHub Top 50
      </a-button>
    </section>

    <section class="stats-row">
      <div class="stat stat-primary">
        <span class="stat-value">{{ store.skills.length }}</span>
        <span class="stat-label">全局技能</span>
      </div>
      <div class="stat">
        <span class="stat-value">{{ store.skillhubSkills.length }}</span>
        <span class="stat-label">SkillHub</span>
      </div>
      <div class="stat">
        <span class="stat-value">{{ categories.length }}</span>
        <span class="stat-label">分类</span>
      </div>
      <div class="stat">
        <span class="stat-value">{{ store.lastSyncCount }}</span>
        <span class="stat-label">最近同步</span>
      </div>
    </section>

    <section class="toolbar">
      <a-input-search
        v-model:value="searchQuery"
        placeholder="搜索 skill 名称、描述或 key"
        allow-clear
        class="search"
      />
      <a-select v-model:value="categoryFilter" class="category-select">
        <a-select-option value="all">全部分类</a-select-option>
        <a-select-option v-for="category in categories" :key="category" :value="category">
          {{ getCategoryLabel(category) }}
        </a-select-option>
      </a-select>
    </section>

    <div class="skills-scroll-shell">
      <a-spin :spinning="store.loading" class="skills-spin">
        <div v-if="filteredSkills.length" class="skill-grid">
          <article v-for="skill in filteredSkills" :key="skill.skill_key" class="skill-card">
            <div class="skill-card-header">
              <img v-if="skill.icon_url" :src="skill.icon_url" :alt="skill.name" class="skill-icon" />
              <div v-else class="skill-icon fallback">{{ skill.name.slice(0, 1).toUpperCase() }}</div>
              <div class="skill-title-block">
                <h2>{{ skill.name }}</h2>
                <span class="skill-key">{{ skill.skill_key }}</span>
              </div>
              <a-tag v-if="skill.source === 'skillhub'" color="blue">SkillHub</a-tag>
            </div>

            <p class="description">{{ skill.description || '暂无描述' }}</p>

            <div class="meta-row">
              <a-tag>{{ getCategoryLabel(skill.category) }}</a-tag>
              <a-tag v-for="tag in getList(skill.sub_categories).slice(0, 2)" :key="tag" color="geekblue">{{ tag }}</a-tag>
              <a-tag v-if="skill.source_rank">Top {{ skill.source_rank }}</a-tag>
            </div>

            <div class="metric-row">
              <span><star-outlined /> {{ skill.stars || 0 }}</span>
              <span><download-outlined /> {{ skill.downloads || 0 }}</span>
              <span><api-outlined /> {{ skill.source_version || 'n/a' }}</span>
            </div>

            <div class="action-row">
              <a-button size="small" type="primary" ghost @click="openSkillDetail(skill)">
                <template #icon><eye-outlined /></template>
                查看详情
              </a-button>
              <a-button size="small" @click="copySkillKey(skill.skill_key)">
                <template #icon><copy-outlined /></template>
                复制 key
              </a-button>
              <a-button v-if="skill.source_url" size="small" type="link" :href="skill.source_url" target="_blank">
                打开来源
              </a-button>
            </div>
          </article>
        </div>
        <a-empty v-else description="没有匹配的 Skill" />
      </a-spin>
    </div>

    <a-modal
      v-model:open="detailOpen"
      :title="selectedSkill?.name || 'Skill 详情'"
      width="min(960px, calc(100vw - 32px))"
      :footer="null"
      :get-container="false"
      class="skill-detail-modal"
    >
      <div v-if="selectedSkill" class="skill-detail">
        <div class="detail-hero">
          <img v-if="selectedSkill.icon_url" :src="selectedSkill.icon_url" :alt="selectedSkill.name" class="detail-icon" />
          <div v-else class="detail-icon fallback">{{ selectedSkill.name.slice(0, 1).toUpperCase() }}</div>
          <div class="detail-title-block">
            <h2>{{ selectedSkill.name }}</h2>
            <p>{{ selectedSkill.description || '暂无描述' }}</p>
            <div class="detail-tags">
              <a-tag color="green">{{ getCategoryLabel(selectedSkill.category) }}</a-tag>
              <a-tag v-if="selectedSkill.source === 'skillhub'" color="blue">SkillHub</a-tag>
              <a-tag v-if="selectedSkill.source_rank">Top {{ selectedSkill.source_rank }}</a-tag>
              <a-tag>{{ getStatusLabel(selectedSkill.status) }}</a-tag>
            </div>
          </div>
        </div>

        <div class="detail-content-grid">
          <div class="detail-main-column">
            <div class="detail-grid">
              <div class="detail-item">
                <span>Skill Key</span>
                <strong>{{ selectedSkill.skill_key }}</strong>
              </div>
              <div class="detail-item">
                <span>成本等级</span>
                <strong>{{ getCostLabel(selectedSkill.cost_level) }}</strong>
              </div>
              <div class="detail-item">
                <span>收藏</span>
                <strong>{{ selectedSkill.stars || 0 }}</strong>
              </div>
              <div class="detail-item">
                <span>下载</span>
                <strong>{{ selectedSkill.downloads || 0 }}</strong>
              </div>
              <div class="detail-item">
                <span>安装</span>
                <strong>{{ selectedSkill.installs || 0 }}</strong>
              </div>
              <div class="detail-item">
                <span>版本</span>
                <strong>{{ selectedSkill.source_version || 'n/a' }}</strong>
              </div>
            </div>

            <div class="detail-section">
              <h3>能力信息</h3>
              <div class="detail-chip-row">
                <span>输入</span>
                <a-tag v-for="item in getList(selectedSkill.input_modalities)" :key="`input-${item}`">
                  {{ getModalityLabel(item) }}
                </a-tag>
                <a-tag v-if="getList(selectedSkill.input_modalities).length === 0">未声明</a-tag>
              </div>
              <div class="detail-chip-row">
                <span>输出</span>
                <a-tag v-for="item in getList(selectedSkill.output_types)" :key="`output-${item}`">
                  {{ getOutputLabel(item) }}
                </a-tag>
                <a-tag v-if="getList(selectedSkill.output_types).length === 0">未声明</a-tag>
              </div>
              <div class="detail-chip-row">
                <span>模型</span>
                <a-tag v-for="item in getList(selectedSkill.required_models)" :key="`model-${item}`" color="geekblue">
                  {{ getModelLabel(item) }}
                </a-tag>
                <a-tag v-if="getList(selectedSkill.required_models).length === 0">无特殊要求</a-tag>
              </div>
              <div class="detail-chip-row">
                <span>工具</span>
                <a-tag v-for="item in getList(selectedSkill.required_tools)" :key="`tool-${item}`" color="purple">
                  {{ getToolLabel(item) }}
                </a-tag>
                <a-tag v-if="getList(selectedSkill.required_tools).length === 0">无外部工具</a-tag>
              </div>
              <div class="detail-chip-row">
                <span>权限</span>
                <a-tag v-for="item in getList(selectedSkill.permission_scope)" :key="`scope-${item}`" color="orange">
                  {{ getPermissionLabel(item) }}
                </a-tag>
                <a-tag v-if="getList(selectedSkill.permission_scope).length === 0">未声明</a-tag>
              </div>
            </div>
          </div>

          <div class="detail-side-column">
            <div class="detail-section detail-source-section" v-if="getList(selectedSkill.sub_categories).length || selectedSkill.source_url">
              <h3>来源与标签</h3>
              <div class="detail-chip-row" v-if="getList(selectedSkill.sub_categories).length">
                <span>子分类</span>
                <a-tag v-for="tag in getList(selectedSkill.sub_categories)" :key="tag" color="cyan">{{ tag }}</a-tag>
              </div>
              <div class="source-line" v-if="selectedSkill.source_url">
                <span>来源链接</span>
                <a :href="selectedSkill.source_url" target="_blank" rel="noreferrer">{{ selectedSkill.source_url }}</a>
              </div>
            </div>

            <div class="detail-actions">
              <a-button @click="copySkillKey(selectedSkill.skill_key)">
                <template #icon><copy-outlined /></template>
                复制 key
              </a-button>
              <a-button v-if="selectedSkill.source_url" type="primary" :href="selectedSkill.source_url" target="_blank">
                打开来源
              </a-button>
            </div>
          </div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import {
  ApiOutlined,
  CloudSyncOutlined,
  CopyOutlined,
  DownloadOutlined,
  EyeOutlined,
  StarOutlined
} from '@ant-design/icons-vue'
import { useSkillStore } from '@/stores/skill'
import type { SkillCatalogItem } from '@/stores/skill'

const store = useSkillStore()
const searchQuery = ref('')
const categoryFilter = ref('all')
const detailOpen = ref(false)
const selectedSkill = ref<SkillCatalogItem | null>(null)

const categoryLabels: Record<string, string> = {
  conversation: '对话问答',
  multimodal: '多模态',
  generation: '内容生成',
  document: '文档处理',
  tooling: '工具调用',
  workflow: '工作流',
  'knowledge-management': '知识管理',
  knowledge: '知识管理',
  productivity: '效率工具',
  research: '研究检索',
  search: '搜索检索',
  data: '数据分析',
  analytics: '数据分析',
  coding: '编程开发',
  development: '编程开发',
  design: '设计创意',
  image: '图像处理',
  audio: '音频处理',
  video: '视频处理',
  writing: '写作编辑',
  marketing: '营销增长',
  business: '商业分析',
  finance: '金融财务',
  education: '教育学习',
  automation: '自动化',
  security: '安全审计',
  general: '通用能力'
}

const getCategoryLabel = (category?: string) => {
  const normalized = String(category || '').trim()
  if (!normalized) return '未分类'
  if (categoryLabels[normalized]) return categoryLabels[normalized]

  return normalized
    .split(/[-_/\s]+/)
    .filter(Boolean)
    .map(part => categoryLabels[part] || part)
    .join(' / ')
}

const simpleLabels: Record<string, string> = {
  text: '文本',
  image: '图片',
  audio: '音频',
  video: '视频',
  file: '文件',
  artifact: '成果物',
  fast: '快速模型',
  reasoning: '推理模型',
  vision: '视觉模型',
  transcribe: '转写模型',
  image_renderer: '图片渲染器',
  file_parser: '文件解析器',
  docx_renderer: '文档渲染器',
  table_renderer: '表格渲染器',
  video_sampler: '视频采样器',
  web_search: '联网搜索',
  artifact_store: '成果存储',
  chat: '聊天会话',
  read_media: '读取媒体',
  write_artifact: '写入成果',
  read_file: '读取文件',
  network: '网络访问',
  skillhub: 'SkillHub'
}

const getSimpleLabel = (value?: string) => {
  const normalized = String(value || '').trim()
  if (!normalized) return '未声明'
  return simpleLabels[normalized] || normalized
}

const getList = (items?: string[]) => {
  return Array.isArray(items) ? items.filter(Boolean) : []
}

const getModalityLabel = getSimpleLabel
const getOutputLabel = getSimpleLabel
const getModelLabel = getSimpleLabel
const getToolLabel = getSimpleLabel
const getPermissionLabel = getSimpleLabel

const getCostLabel = (cost?: string) => {
  const labels: Record<string, string> = {
    low: '低',
    medium: '中',
    high: '高'
  }
  return labels[String(cost || '').toLowerCase()] || cost || '未声明'
}

const getStatusLabel = (status?: string) => {
  const labels: Record<string, string> = {
    active: '可用',
    inactive: '停用',
    beta: '测试中'
  }
  return labels[String(status || '').toLowerCase()] || status || '未知状态'
}

const categories = computed(() => {
  return Array.from(new Set(store.skills.map(skill => skill.category).filter(Boolean))).sort()
})

const filteredSkills = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  return store.skills.filter(skill => {
    const categoryMatches = categoryFilter.value === 'all' || skill.category === categoryFilter.value
    const queryMatches =
      !query ||
      skill.name.toLowerCase().includes(query) ||
      skill.skill_key.toLowerCase().includes(query) ||
      (skill.description || '').toLowerCase().includes(query)
    return categoryMatches && queryMatches
  })
})

const handleSync = async () => {
  try {
    await store.syncSkillHub(50)
    message.success(`已同步 ${store.lastSyncCount} 个 SkillHub 技能`)
  } catch {
    message.error('同步 SkillHub 失败，请稍后重试')
  }
}

const copySkillKey = async (skillKey: string) => {
  try {
    await navigator.clipboard?.writeText(skillKey)
    message.success('已复制 skill key')
  } catch {
    message.info(skillKey)
  }
}

const openSkillDetail = (skill: SkillCatalogItem) => {
  selectedSkill.value = skill
  detailOpen.value = true
}

onMounted(() => {
  store.fetchSkills()
})
</script>

<style scoped>
.skill-repository-view {
  height: 100vh;
  box-sizing: border-box;
  overflow: hidden;
  padding: 24px 28px 32px;
  color: #1f2937;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.skills-scroll-shell {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 8px;
  overscroll-behavior: contain;
  scroll-behavior: smooth;
}

.skills-spin {
  display: block;
  min-height: 100%;
}

.skills-spin :deep(.ant-spin-container) {
  min-height: 100%;
}

.skills-scroll-shell::-webkit-scrollbar {
  width: 10px;
}

.skills-scroll-shell::-webkit-scrollbar-track {
  background: rgba(229, 236, 231, 0.8);
  border-radius: 999px;
}

.skills-scroll-shell::-webkit-scrollbar-thumb {
  background: #b7c8bd;
  border-radius: 999px;
  border: 2px solid rgba(229, 236, 231, 0.8);
}

.skills-scroll-shell::-webkit-scrollbar-thumb:hover {
  background: #8fb39d;
}

.page-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
  background: linear-gradient(135deg, var(--brand-primary) 0%, var(--brand-primary-dark) 100%);
  border: 1px solid var(--brand-primary-dark);
  border-radius: 12px;
  box-shadow: 0 12px 28px var(--brand-primary-shadow);
  margin-bottom: 16px;
}

.page-band h1 {
  margin: 0;
  color: #ffffff;
  font-size: 24px;
  line-height: 1.25;
}

.page-band p {
  margin: 6px 0 0;
  color: rgba(255, 255, 255, 0.86);
  font-size: 14px;
}

.page-band :deep(.ant-btn-primary) {
  background: #ffffff;
  border-color: #ffffff;
  color: var(--brand-primary-dark);
  box-shadow: 0 8px 18px rgba(24, 31, 27, 0.14);
}

.page-band :deep(.ant-btn-primary:hover) {
  background: var(--brand-primary-light);
  border-color: var(--brand-primary-light);
  color: var(--brand-primary-dark);
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0 18px;
  flex-wrap: wrap;
  padding: 2px 0;
}

.search {
  width: min(420px, 100%);
}

.category-select {
  width: 180px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.stat {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 108px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 12px 30px rgba(24, 31, 27, 0.06);
}

.stat::after {
  content: '';
  position: absolute;
  right: -28px;
  bottom: -36px;
  width: 110px;
  height: 110px;
  border-radius: 50%;
  background: rgba(59, 179, 107, 0.08);
}

.stat-primary {
  background: #151917;
  border-color: #151917;
}

.stat-primary .stat-value {
  color: #bee83f;
}

.stat-primary .stat-label {
  color: #e5efdf;
}

.stat-value {
  font-size: 28px;
  font-weight: 800;
  color: #111827;
  line-height: 1.1;
}

.stat-label {
  color: #6b7280;
  font-size: 14px;
  font-weight: 600;
}

.skill-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
  padding-bottom: 4px;
}

.skill-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  min-height: 260px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;
}

.skill-card:hover {
  border-color: #b7d9c4;
  box-shadow: 0 16px 32px rgba(24, 31, 27, 0.08);
  transform: translateY(-2px);
}

.skill-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.skill-icon {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  object-fit: cover;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  flex: 0 0 auto;
}

.skill-icon.fallback {
  display: grid;
  place-items: center;
  color: #3158d4;
  font-weight: 700;
}

.skill-title-block {
  min-width: 0;
  flex: 1;
}

.skill-title-block h2 {
  margin: 0;
  font-size: 16px;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.skill-key {
  color: #6b7280;
  font-size: 12px;
  overflow-wrap: anywhere;
}

.description {
  color: #4b5563;
  font-size: 13px;
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.meta-row,
.metric-row,
.action-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.metric-row {
  color: #6b7280;
  font-size: 12px;
  margin-top: auto;
}

.action-row {
  justify-content: flex-end;
}

.action-row :deep(.ant-btn-primary.ant-btn-background-ghost) {
  border-color: #3bb36b;
  color: #2f9b5d;
}

.action-row :deep(.ant-btn-primary.ant-btn-background-ghost:hover) {
  border-color: #2f9b5d;
  color: #247c4a;
}

:global(.skill-detail-modal .ant-modal-content) {
  max-height: calc(100vh - 48px);
  display: flex;
  flex-direction: column;
  border-radius: 18px;
  overflow: hidden;
}

:global(.skill-detail-modal .ant-modal-header) {
  flex: 0 0 auto;
  padding: 22px 24px 8px;
  border-bottom: none;
}

:global(.skill-detail-modal .ant-modal-title) {
  color: #111827;
  font-size: 20px;
  font-weight: 800;
}

:global(.skill-detail-modal .ant-modal-body) {
  min-height: 0;
  flex: 1 1 auto;
  padding: 12px 24px 24px;
  overflow: auto;
}

.skill-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-hero {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 16px;
  padding: 16px;
  border: 1px solid #e6eee8;
  border-radius: 14px;
  background: #f8fbf8;
}

.detail-content-grid {
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(250px, 0.38fr);
  gap: 14px;
  align-items: start;
}

.detail-main-column,
.detail-side-column {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-side-column {
  position: sticky;
  top: 0;
}

.detail-icon {
  width: 58px;
  height: 58px;
  border-radius: 14px;
  object-fit: cover;
  border: 1px solid #e0e7e2;
  background: #ffffff;
  flex-shrink: 0;
}

.detail-icon.fallback {
  display: grid;
  place-items: center;
  color: #3bb36b;
  font-size: 22px;
  font-weight: 850;
}

.detail-title-block {
  min-width: 0;
}

.detail-title-block h2 {
  margin: 0;
  color: #111827;
  font-size: 20px;
  line-height: 1.25;
}

.detail-title-block p {
  margin: 8px 0 12px;
  color: #4b5563;
  line-height: 1.6;
}

.detail-tags,
.detail-chip-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.detail-item {
  min-width: 0;
  border: 1px solid #e5ece7;
  border-radius: 12px;
  background: #ffffff;
  padding: 12px;
}

.detail-item span {
  display: block;
  color: #738078;
  font-size: 12px;
  margin-bottom: 6px;
}

.detail-item strong {
  display: block;
  color: #111827;
  font-size: 14px;
  overflow-wrap: anywhere;
}

.detail-section {
  border: 1px solid #e5ece7;
  border-radius: 14px;
  padding: 14px;
  background: #ffffff;
}

.detail-source-section {
  max-height: 310px;
  overflow: auto;
}

.detail-section h3 {
  margin: 0 0 12px;
  color: #111827;
  font-size: 15px;
  font-weight: 800;
}

.detail-chip-row {
  min-height: 32px;
  padding: 7px 0;
  border-top: 1px solid #f0f4f1;
}

.detail-chip-row:first-of-type {
  border-top: none;
  padding-top: 0;
}

.detail-chip-row > span,
.source-line > span {
  width: 68px;
  color: #738078;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
}

.source-line {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding-top: 4px;
}

.source-line a {
  color: #2f9b5d;
  word-break: break-all;
}

.detail-actions {
  display: flex;
  justify-content: stretch;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  border: 1px solid #e5ece7;
  border-radius: 14px;
  background: #ffffff;
}

.detail-actions :deep(.ant-btn) {
  width: 100%;
}

@media (max-width: 760px) {
  .skill-repository-view {
    height: 100vh;
    overflow: hidden;
    padding: 16px;
  }

  .page-band {
    align-items: flex-start;
    flex-direction: column;
  }

  .stats-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .skill-grid {
    grid-template-columns: 1fr;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .detail-content-grid {
    grid-template-columns: 1fr;
  }

  .detail-side-column {
    position: static;
  }

  .detail-hero {
    grid-template-columns: 1fr;
  }

  .detail-actions {
    flex-direction: column;
  }
}
</style>
