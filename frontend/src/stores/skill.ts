import { defineStore } from 'pinia'
import request from '@/utils/request'

export interface SkillCatalogItem {
  skill_key: string
  name: string
  category: string
  description?: string
  input_modalities: string[]
  output_types: string[]
  required_models: string[]
  required_tools: string[]
  params_schema: Record<string, unknown>
  permission_scope: string[]
  cost_level: string
  status: string
  source?: string
  source_url?: string
  source_slug?: string
  source_rank?: number
  source_owner?: string
  source_version?: string
  icon_url?: string
  downloads: number
  installs: number
  stars: number
  score?: number
  sub_categories: string[]
  synced_at?: string
}

export const useSkillStore = defineStore('skill', {
  state: () => ({
    skills: [] as SkillCatalogItem[],
    loading: false,
    syncing: false,
    error: null as string | null,
    lastSyncCount: 0
  }),
  getters: {
    skillhubSkills: (state) => state.skills.filter(skill => skill.source === 'skillhub')
  },
  actions: {
    async fetchSkills() {
      this.loading = true
      this.error = null
      try {
        const res = await request.get('/skills/catalog')
        this.skills = Array.isArray(res.data) ? res.data : []
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to fetch skills'
        this.skills = []
      } finally {
        this.loading = false
      }
    },
    async syncSkillHub(limit = 50) {
      this.syncing = true
      this.error = null
      try {
        const res = await request.post('/skills/sync/skillhub', null, { params: { limit } })
        this.lastSyncCount = Number(res.data?.count || 0)
        await this.fetchSkills()
      } catch (error) {
        this.error = error instanceof Error ? error.message : 'Failed to sync SkillHub'
        throw error
      } finally {
        this.syncing = false
      }
    }
  }
})
