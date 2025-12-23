// Re-export types from API service
export type {
  Profile,
  WorkExperience,
  Education,
  ProfileStats,
  Job,
  JobLog,
  DashboardStats,
  TeamMember,
} from '../services/api'

// Additional frontend-specific types

export type JobStatus =
  | 'pending'
  | 'queued'
  | 'in_progress'
  | 'awaiting_otp'
  | 'awaiting_captcha'
  | 'awaiting_user'
  | 'awaiting_action'
  | 'submitted'
  | 'applied'
  | 'failed'
  | 'cancelled'
  | 'duplicate'

export interface StatusConfig {
  label: string
  color: 'success' | 'warning' | 'error' | 'info' | 'neutral'
  description: string
}

export const JOB_STATUS_CONFIG: Record<JobStatus, StatusConfig> = {
  pending: {
    label: 'Pending',
    color: 'neutral',
    description: 'Waiting to be processed',
  },
  queued: {
    label: 'Queued',
    color: 'info',
    description: 'In queue for processing',
  },
  in_progress: {
    label: 'In Progress',
    color: 'info',
    description: 'Currently being processed',
  },
  awaiting_otp: {
    label: 'Awaiting OTP',
    color: 'warning',
    description: 'Requires OTP verification',
  },
  awaiting_captcha: {
    label: 'Awaiting CAPTCHA',
    color: 'warning',
    description: 'Requires CAPTCHA solution',
  },
  awaiting_user: {
    label: 'Awaiting User',
    color: 'warning',
    description: 'Requires user intervention',
  },
  awaiting_action: {
    label: 'Action Required',
    color: 'warning',
    description: 'Requires manual action (CAPTCHA, etc.)',
  },
  submitted: {
    label: 'Submitted',
    color: 'info',
    description: 'Form submitted, awaiting confirmation',
  },
  applied: {
    label: 'Applied',
    color: 'success',
    description: 'Successfully applied',
  },
  failed: {
    label: 'Failed',
    color: 'error',
    description: 'Application failed',
  },
  cancelled: {
    label: 'Cancelled',
    color: 'neutral',
    description: 'Application cancelled',
  },
  duplicate: {
    label: 'Duplicate',
    color: 'neutral',
    description: 'Already applied to this job',
  },
}

export interface NotificationPayload {
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  jobId?: string
  action?: {
    label: string
    href?: string
    onClick?: () => void
  }
}

