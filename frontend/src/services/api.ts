import axios from 'axios'

// API client instance
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// ============================================
// PROFILE TYPES
// ============================================

export interface DocumentContent {
  filename: string
  path: string
  content: string
  format_type: 'pdf' | 'docx' | 'markdown' | 'text' | 'error'
}

export interface WorkExperience {
  company_name: string
  job_title: string
  work_style: 'remote' | 'hybrid' | 'onsite'
  start_date: string
  end_date?: string
  address_1?: string
  address_2?: string
  city?: string
  state?: string
  country?: string
  zip_code?: string
  document_paths: string[]
  document_contents?: DocumentContent[]
}

export interface Education {
  university_name: string
  degree: string
  major?: string
  location?: string
  start_date?: string
  end_date?: string
}

export interface Profile {
  id: string
  
  // Name fields
  first_name: string
  middle_name?: string
  last_name: string
  preferred_first_name?: string
  name: string  // Computed display name
  
  // Contact
  email: string
  phone?: string
  location?: string
  preferred_password?: string
  
  // Detailed Address for Job Applications
  address_1?: string
  address_2?: string
  county?: string
  city?: string
  state?: string
  country?: string
  zip_code?: string
  
  // Online Presence
  linkedin_url?: string
  github_url?: string
  portfolio_url?: string
  
  // Demographics & Work Preferences
  gender?: string
  nationality?: string
  veteran_status?: string
  disability_status?: string
  willing_to_travel: boolean
  willing_to_relocate: boolean
  primary_language?: string
  
  // Documents & Experience
  resume_path?: string
  cover_letter_template?: string
  cover_letter_template_path?: string
  work_experience: WorkExperience[]
  education: Education[]
  skills: string[]
  custom_fields: Record<string, string>
  
  // AI Customization (per-profile overrides)
  personal_brand?: string
  key_achievements?: string[]
  priority_skills?: string[]
  target_industries?: string[]
  target_roles?: string[]
  resume_tone_override?: string
  custom_question_answers?: Record<string, string>
  salary_min?: number
  salary_max?: number
  salary_currency?: string
  
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProfileStats {
  total_applications: number
  pending: number
  in_progress: number
  applied: number
  failed: number
  awaiting_action: number
}

// ============================================
// JOB TYPES
// ============================================

export interface Job {
  id: string
  profile_id: string
  url: string
  url_hash: string
  company_name?: string
  job_title?: string
  location?: string
  salary_range?: string
  status: string
  error_message?: string
  confirmation_reference?: string
  retry_count: number
  max_retries: number
  priority: number
  metadata?: Record<string, unknown>
  created_at: string
  updated_at: string
  started_at?: string
  applied_at?: string
}

export interface JobLog {
  id: string
  action: string
  details?: Record<string, unknown>
  screenshot_path?: string
  created_at: string
}

// ============================================
// DASHBOARD TYPES
// ============================================

export interface DashboardStats {
  total_applications: number
  recent_applications: number
  by_status: {
    pending: number
    in_progress: number
    applied: number
    failed: number
    awaiting_action: number
    cancelled: number
  }
  success_rate: number
  period_days: number
}

export interface TeamMember {
  id: string
  name: string
  email: string
  stats: {
    total: number
    applied: number
    pending: number
    in_progress: number
    awaiting_action: number
  }
}

// ============================================
// PROFILE API
// ============================================

export const profileApi = {
  list: async (activeOnly = true) => {
    const { data } = await api.get<{ profiles: Profile[]; total: number }>(
      '/profiles',
      { params: { active_only: activeOnly } }
    )
    return data
  },

  get: async (id: string) => {
    const { data } = await api.get<Profile & { stats: ProfileStats }>(
      `/profiles/${id}`
    )
    return data
  },

  create: async (profile: Partial<Profile>) => {
    const { data } = await api.post<Profile>('/profiles', profile)
    return data
  },

  update: async (id: string, profile: Partial<Profile>) => {
    const { data } = await api.put<Profile>(`/profiles/${id}`, profile)
    return data
  },

  delete: async (id: string) => {
    await api.delete(`/profiles/${id}`)
  },

  uploadResume: async (id: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post<Profile>(
      `/profiles/${id}/resume`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return data
  },

  uploadWorkDocuments: async (id: string, workExperienceIndex: number, files: File[]) => {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    const { data } = await api.post<{
      message: string
      document_paths: string[]
      work_experience: WorkExperience
    }>(
      `/profiles/${id}/work-documents`,
      formData,
      { 
        headers: { 'Content-Type': 'multipart/form-data' },
        params: { work_experience_index: workExperienceIndex }
      }
    )
    return data
  },

  deleteWorkDocument: async (id: string, workExperienceIndex: number, documentPath: string) => {
    const { data } = await api.delete<{ 
      message: string
      document_paths: string[]
      work_experience: WorkExperience 
    }>(
      `/profiles/${id}/work-documents/${workExperienceIndex}`,
      { params: { document_path: documentPath } }
    )
    return data
  },

  getDocumentContent: async (id: string, workExperienceIndex: number, documentPath: string) => {
    const { data } = await api.get<DocumentContent>(
      `/profiles/${id}/work-documents/${workExperienceIndex}/content`,
      { params: { document_path: documentPath } }
    )
    return data
  },

  getStats: async (id: string) => {
    const { data } = await api.get<ProfileStats>(`/profiles/${id}/stats`)
    return data
  },

  getResumeFileUrl: (id: string) => {
    return `/api/profiles/${id}/resume/file`
  },

  deleteResume: async (id: string) => {
    const { data } = await api.delete<Profile>(`/profiles/${id}/resume`)
    return data
  },

  uploadCoverLetterTemplate: async (id: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post<Profile>(
      `/profiles/${id}/cover-letter-template`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return data
  },

  deleteCoverLetterTemplate: async (id: string) => {
    const { data } = await api.delete<Profile>(`/profiles/${id}/cover-letter-template`)
    return data
  },

  getCoverLetterTemplateFileUrl: (id: string) => {
    return `/api/profiles/${id}/cover-letter-template/file`
  },

  generateCoverLetter: async (id: string, content: string) => {
    const { data } = await api.post<{ generation_id: string; file_path: string; file_type: string }>(
      `/profiles/${id}/cover-letter-template/generate`,
      null,
      { params: { content } }
    )
    return data
  },

  getGeneratedCoverLetterUrl: (profileId: string, generationId: string) => {
    return `/api/profiles/${profileId}/cover-letter-template/generated/${generationId}`
  },

  deleteGeneratedCoverLetter: async (profileId: string, generationId: string) => {
    await api.delete(`/profiles/${profileId}/cover-letter-template/generated/${generationId}`)
  },
}

// ============================================
// JOB API
// ============================================

export const jobApi = {
  list: async (params: {
    profile_id?: string
    status?: string[]
    page?: number
    page_size?: number
  } = {}) => {
    const { data } = await api.get<{
      jobs: Job[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>('/jobs', { params })
    return data
  },

  get: async (id: string) => {
    const { data } = await api.get<Job & { logs: JobLog[] }>(`/jobs/${id}`)
    return data
  },

  create: async (job: { profile_id: string; url: string; priority?: number }) => {
    const { data } = await api.post<Job>('/jobs', job)
    return data
  },

  createBulk: async (data: {
    profile_id: string
    urls: string[]
    priority?: number
  }) => {
    const { data: result } = await api.post<{
      created: number
      duplicates: number
      errors: number
      job_ids: string[]
      duplicate_urls: string[]
      error_messages: string[]
    }>('/jobs/bulk', data)
    return result
  },

  update: async (id: string, job: Partial<Job>) => {
    const { data } = await api.put<Job>(`/jobs/${id}`, job)
    return data
  },

  delete: async (id: string) => {
    await api.delete(`/jobs/${id}`)
  },

  retry: async (id: string) => {
    const { data } = await api.post<Job>(`/jobs/${id}/retry`)
    return data
  },

  resume: async (id: string) => {
    const { data } = await api.post<Job>(`/jobs/${id}/resume`)
    return data
  },

  startProcessing: async (profileId?: string, limit = 10) => {
    const { data } = await api.post<{ message: string; queued: number }>(
      '/jobs/start-processing',
      null,
      { params: { profile_id: profileId, limit } }
    )
    return data
  },

  getHistory: async (jobId: string, limit = 100) => {
    const { data } = await api.get<{
      job_id: string
      history: Array<{
        id: string
        action: string
        details: Record<string, unknown>
        screenshot_path?: string
        created_at: string
      }>
      count: number
    }>(`/jobs/${jobId}/history`, { params: { limit } })
    return data
  },

  getSummary: async (jobId: string) => {
    const { data } = await api.get<{
      job_id: string
      job_status: string
      job_url: string
      company_name?: string
      job_title?: string
      summary: {
        total_actions: number
        fields_filled: number
        fields_failed: number
        pages_processed: number
        captcha_encounters: number
        errors: number
      }
      session?: {
        status: string
        current_page: number
        pages_processed: number
        autofill_results_count: number
      }
    }>(`/jobs/${jobId}/summary`)
    return data
  },

  getDetail: async (jobId: string) => {
    const { data } = await api.get<{
      job: {
        id: string
        url: string
        company_name?: string
        job_title?: string
        location?: string
        status: string
        error_message?: string
        retry_count: number
        profile_id: string
        profile_name: string
        created_at: string
        updated_at: string
        started_at?: string
        applied_at?: string
      }
      history: Array<{
        id: string
        action: string
        details: Record<string, unknown>
        created_at: string
      }>
      autofill_results: Array<{
        field_name: string
        selector: string
        action: string
        success: boolean
        error?: string
      }>
      page_snapshots: Array<{
        url: string
        title: string
        page_number: number
        inputs_count: number
        buttons_count: number
        timestamp: string
      }>
    }>(`/jobs/${jobId}/detail`)
    return data
  },
}

// ============================================
// DASHBOARD API
// ============================================

export const dashboardApi = {
  getStats: async (profileId?: string, days = 7) => {
    const { data } = await api.get<DashboardStats>('/dashboard/stats', {
      params: { profile_id: profileId, days },
    })
    return data
  },

  getTeam: async () => {
    const { data } = await api.get<{ team: TeamMember[]; total_members: number }>(
      '/dashboard/team'
    )
    return data
  },

  getActivity: async (limit = 50, profileId?: string) => {
    const { data } = await api.get<{
      activities: Array<{
        id: string
        action: string
        details?: Record<string, unknown>
        created_at: string
        job: { title: string; company: string; url: string }
        profile: string
      }>
    }>('/dashboard/activity', {
      params: { limit, profile_id: profileId },
    })
    return data
  },

  getChartData: async (days = 30, profileId?: string) => {
    const { data } = await api.get<{
      data: Array<{ date: string; count: number }>
      period_days: number
    }>('/dashboard/charts/applications-over-time', {
      params: { days, profile_id: profileId },
    })
    return data
  },
}

// ============================================
// APPLICATION LOGS API
// ============================================

export const applicationApi = {
  getLogs: async (jobId: string, limit = 100) => {
    const { data } = await api.get<JobLog[]>(`/applications/${jobId}/logs`, {
      params: { limit },
    })
    return data
  },

  getScreenshotUrl: (jobId: string, logId: string) => {
    return `/api/applications/${jobId}/screenshot/${logId}`
  },
}

// ============================================
// AI SETTINGS TYPES
// ============================================

export interface AvailableModel {
  id: string
  name: string
  created?: number
}

export interface AISettings {
  id: string
  
  // AI Provider Configuration
  openai_api_key_masked?: string
  openai_model: string
  temperature: number
  max_tokens: number
  available_models: AvailableModel[]
  
  // Feature Toggles
  enable_resume_generation: boolean
  enable_cover_letter_generation: boolean
  enable_answer_generation: boolean
  
  // Resume Settings
  resume_system_prompt?: string
  resume_tone: 'professional' | 'creative' | 'technical' | 'executive'
  resume_format: 'bullet' | 'narrative' | 'hybrid'
  resume_max_pages: number
  
  // Cover Letter Settings
  cover_letter_system_prompt?: string
  cover_letter_tone: 'professional' | 'creative' | 'technical' | 'executive'
  cover_letter_length: 'short' | 'medium' | 'long'
  
  // Question Prompts
  question_prompts: Record<string, string>
  
  // Default Answers
  default_answers: Record<string, string>
  
  // Browser Automation Settings
  max_concurrent_jobs: number
  browser_timeout: number
  browser_headless: boolean
  screenshot_on_error: boolean
  auto_retry_failed: boolean
  max_retries: number
  
  // Fallback Settings
  ai_timeout_seconds: number
  use_fallback_on_error: boolean
  
  created_at: string
  updated_at: string
}

export interface AISettingsUpdate {
  openai_api_key?: string
  openai_model?: string
  temperature?: number
  max_tokens?: number
  enable_resume_generation?: boolean
  enable_cover_letter_generation?: boolean
  enable_answer_generation?: boolean
  resume_system_prompt?: string
  resume_tone?: string
  resume_format?: string
  resume_max_pages?: number
  cover_letter_system_prompt?: string
  cover_letter_tone?: string
  cover_letter_length?: string
  question_prompts?: Record<string, string>
  default_answers?: Record<string, string>
  max_concurrent_jobs?: number
  browser_timeout?: number
  browser_headless?: boolean
  screenshot_on_error?: boolean
  auto_retry_failed?: boolean
  max_retries?: number
  ai_timeout_seconds?: number
  use_fallback_on_error?: boolean
}

export interface QuestionPromptInfo {
  key: string
  name: string
  description?: string
}

export interface FormFieldInfo {
  key: string
  name: string
  type: string
}

export interface AIDefaultsResponse {
  question_prompts: Record<string, string>
  question_prompts_list: QuestionPromptInfo[]
  default_answers: Record<string, string>
  form_fields_list: FormFieldInfo[]
}

// ============================================
// AI SETTINGS API
// ============================================

export const aiSettingsApi = {
  get: async () => {
    const { data } = await api.get<AISettings>('/ai-settings')
    return data
  },

  update: async (settings: AISettingsUpdate) => {
    const { data } = await api.put<AISettings>('/ai-settings', settings)
    return data
  },

  getDefaults: async () => {
    const { data } = await api.get<AIDefaultsResponse>('/ai-settings/defaults')
    return data
  },

  resetPrompts: async () => {
    const { data } = await api.post<{ message: string; success: boolean }>(
      '/ai-settings/reset-prompts'
    )
    return data
  },

  testConnection: async () => {
    const { data } = await api.post<{
      success: boolean
      message: string
      model?: string
      response?: string
      models: AvailableModel[]
    }>('/ai-settings/test-connection')
    return data
  },
}

// ============================================
// NOTIFICATIONS API
// ============================================

export interface SystemNotification {
  type: string
  title: string
  message: string
  job_id?: string
  profile_id?: string
  priority: 'low' | 'normal' | 'high' | 'urgent'
  data?: Record<string, unknown>
  action_url?: string
  requires_action: boolean
  created_at: string
}

export interface NotificationsResponse {
  notifications: SystemNotification[]
  count: number
}

export const notificationsApi = {
  getAll: async (limit: number = 50, jobId?: string): Promise<NotificationsResponse> => {
    const params = new URLSearchParams({ limit: limit.toString() })
    if (jobId) params.append('job_id', jobId)
    const { data } = await api.get<NotificationsResponse>(`/jobs/notifications/all?${params}`)
    return data
  },
}

export default api
