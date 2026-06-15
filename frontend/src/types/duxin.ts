export type DuxinMode = 'support' | 'relationship' | 'growth' | 'crisis'
export type DuxinRiskLevel = 'L0' | 'L1' | 'L2' | 'L3'
export type DuxinMemoryType = 'preference' | 'trigger' | 'support_method' | 'goal' | 'note'
export type DuxinFeedbackRating = 'helpful' | 'not_helpful' | 'needs_follow_up'

export interface DuxinTeamMember {
  key: string
  name: string
  role: string
  style: string
  focus: string
}

export interface DuxinTeamPlan {
  mode: DuxinMode
  primary_agent: DuxinTeamMember
  members: DuxinTeamMember[]
  handoff_reason: string
  summary: string
}

export interface DuxinMessageMetadata extends Record<string, unknown> {
  risk?: Record<string, unknown>
  team?: DuxinTeamPlan
  fallback?: boolean
  error?: string
  source?: string
}

export interface DuxinSession {
  id: number
  user_id: number
  title: string
  mode: DuxinMode
  risk_level: DuxinRiskLevel
  status: string
  summary?: string | null
  latest_message_at?: string | null
  created_at: string
  updated_at: string
}

export interface DuxinMessage {
  id: number
  session_id: number
  user_id: number
  role: 'user' | 'assistant' | 'system'
  agent_name?: string | null
  content: string
  risk_level: DuxinRiskLevel
  metadata: DuxinMessageMetadata
  created_at: string
  clientId?: string
}

export interface DuxinMemory {
  id: number
  user_id: number
  memory_type: DuxinMemoryType
  content: string
  source_session_id?: number | null
  user_editable: boolean
  created_at: string
}

export interface DuxinMemorySummaryItem extends DuxinMemory {}

export interface DuxinMemorySummary {
  total: number
  by_type: Partial<Record<DuxinMemoryType, number>>
  recent: DuxinMemorySummaryItem[]
}

export interface DuxinRiskAssessment {
  risk_level: DuxinRiskLevel
  signals: string[]
  response_mode: 'support' | 'stabilize' | 'crisis'
  should_escalate: boolean
  summary: string
  recommended_actions: string[]
}

export interface DuxinFeedback {
  id: number
  user_id: number
  session_id?: number | null
  rating: DuxinFeedbackRating
  content?: string | null
  risk_level?: DuxinRiskLevel | null
  linked_memory_id?: number | null
  created_at: string
}

export interface DuxinFeedbackSummary {
  total: number
  helpful: number
  not_helpful: number
  needs_follow_up: number
  by_risk_level: Partial<Record<DuxinRiskLevel, number>>
  recent: DuxinFeedback[]
}
