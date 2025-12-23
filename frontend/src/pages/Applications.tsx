import { useState, useEffect } from 'react'
import { 
  Search,
  CheckCircle,
  Clock,
  AlertTriangle,
  XCircle,
  ExternalLink,
  Eye,
  ChevronDown,
  Loader2,
  RefreshCw,
  Play
} from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { useJobStore } from '../stores/jobStore'
import { useProfileStore } from '../stores/profileStore'
import { JOB_STATUS_CONFIG, type JobStatus } from '../types'

const COLOR_STYLES = {
  success: { 
    icon: CheckCircle, 
    className: 'badge-success',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/20'
  },
  warning: { 
    icon: AlertTriangle, 
    className: 'badge-warning',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/20'
  },
  error: { 
    icon: XCircle, 
    className: 'badge-error',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/20'
  },
  info: { 
    icon: Clock, 
    className: 'badge-info',
    bgColor: 'bg-primary-500/10',
    borderColor: 'border-primary-500/20'
  },
  neutral: { 
    icon: Clock, 
    className: 'badge-neutral',
    bgColor: 'bg-surface-500/10',
    borderColor: 'border-surface-500/20'
  },
}

const getStatusDisplay = (status: string) => {
  const config = JOB_STATUS_CONFIG[status as JobStatus]
  if (!config) {
    return { ...COLOR_STYLES.neutral, label: status }
  }
  return { ...COLOR_STYLES[config.color], label: config.label }
}

export default function Applications() {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { 
    jobs, 
    isLoading, 
    fetchJobs,
    retryJob,
    resumeJob,
  } = useJobStore()

  const { profiles, fetchProfiles } = useProfileStore()

  useEffect(() => {
    fetchJobs()
    fetchProfiles()
  }, [fetchJobs, fetchProfiles])

  // Filter to show only jobs that have been processed (not pending)
  const applications = jobs.filter(job => 
    job.status !== 'pending' && job.status !== 'queued'
  )

  const filteredApplications = applications.filter(app => {
    const matchesSearch = 
      (app.company_name?.toLowerCase().includes(searchQuery.toLowerCase()) || false) ||
      (app.job_title?.toLowerCase().includes(searchQuery.toLowerCase()) || false) ||
      app.url.toLowerCase().includes(searchQuery.toLowerCase())
    
    const matchesStatus = statusFilter === 'all' || app.status === statusFilter

    return matchesSearch && matchesStatus
  })

  const appliedCount = applications.filter(a => a.status === 'applied').length
  const successRate = applications.length > 0 
    ? Math.round((appliedCount / applications.length) * 100) 
    : 0

  const handleRetry = async (id: string) => {
    try {
      await retryJob(id)
      toast.success('Job queued for retry')
    } catch {
      toast.error('Failed to retry')
    }
  }

  const handleResume = async (id: string) => {
    try {
      await resumeJob(id)
      toast.success('Job resumed')
    } catch {
      toast.error('Failed to resume')
    }
  }

  const getProfileName = (profileId: string) => {
    return profiles.find(p => p.id === profileId)?.name || 'Unknown'
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">Applications</h1>
          <p className="text-surface-400 mt-1">Track all submitted job applications</p>
        </div>
        <div className="flex items-center gap-4">
          <button 
            onClick={() => fetchJobs()}
            disabled={isLoading}
            className="btn-secondary"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
            Refresh
          </button>
          <div className="text-right">
            <p className="text-2xl font-bold text-emerald-400">{successRate}%</p>
            <p className="text-xs text-surface-500">Success Rate</p>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-500" />
          <input
            type="text"
            placeholder="Search applications..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-12"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="input w-auto"
        >
          <option value="all">All Statuses</option>
          <option value="applied">Applied</option>
          <option value="in_progress">In Progress</option>
          <option value="awaiting_otp">Awaiting OTP</option>
          <option value="awaiting_captcha">Awaiting CAPTCHA</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Loading State */}
      {isLoading && applications.length === 0 ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
        </div>
      ) : filteredApplications.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="w-16 h-16 mx-auto rounded-full bg-surface-800 flex items-center justify-center mb-4">
            <Search className="w-8 h-8 text-surface-500" />
          </div>
          <h3 className="text-lg font-medium text-white">No applications found</h3>
          <p className="text-surface-400 mt-1">
            {statusFilter !== 'all' 
              ? 'Try changing your filter or search query'
              : 'Start by adding some jobs to the queue and processing them'}
          </p>
        </div>
      ) : (
        /* Applications List */
        <div className="space-y-3">
          {filteredApplications.map((app) => {
            const status = getStatusDisplay(app.status)
            const isExpanded = expandedId === app.id
            const profileName = getProfileName(app.profile_id)

            return (
              <div 
                key={app.id} 
                className={clsx(
                  "card overflow-hidden transition-all",
                  status.bgColor,
                  status.borderColor,
                  "border"
                )}
              >
                {/* Main row */}
                <div 
                  className="p-4 flex items-center gap-4 cursor-pointer hover:bg-surface-800/30"
                  onClick={() => setExpandedId(isExpanded ? null : app.id)}
                >
                  {/* Company Icon */}
                  <div className="w-12 h-12 rounded-xl bg-surface-800 flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-bold text-white">
                      {(app.company_name || app.url).slice(0, 2).toUpperCase()}
                    </span>
                  </div>

                  {/* Job Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-medium text-white truncate">
                        {app.job_title || 'Untitled Position'}
                      </h3>
                      <span className={status.className}>
                        <status.icon className="w-3 h-3 mr-1" />
                        {status.label}
                      </span>
                    </div>
                    <p className="text-sm text-surface-400 mt-0.5">
                      {app.company_name || new URL(app.url).hostname} • {profileName}
                    </p>
                  </div>

                  {/* Date & Actions */}
                  <div className="flex items-center gap-4">
                    {app.applied_at && (
                      <div className="text-right hidden sm:block">
                        <p className="text-sm text-surface-300">
                          {new Date(app.applied_at).toLocaleDateString()}
                        </p>
                        <p className="text-xs text-surface-500">
                          {new Date(app.applied_at).toLocaleTimeString()}
                        </p>
                      </div>
                    )}
                    <ChevronDown 
                      className={clsx(
                        "w-5 h-5 text-surface-500 transition-transform",
                        isExpanded && "rotate-180"
                      )}
                    />
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="px-4 pb-4 pt-2 border-t border-surface-800/50 space-y-4 animate-slide-down">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-surface-500 uppercase tracking-wider mb-1">
                          Job URL
                        </p>
                        <a 
                          href={app.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-primary-400 hover:text-primary-300 flex items-center gap-1"
                        >
                          {app.url.slice(0, 50)}...
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                      {app.confirmation_reference && (
                        <div>
                          <p className="text-xs text-surface-500 uppercase tracking-wider mb-1">
                            Confirmation Reference
                          </p>
                          <p className="text-sm text-surface-300 font-mono">
                            {app.confirmation_reference}
                          </p>
                        </div>
                      )}
                      {app.error_message && (
                        <div className="sm:col-span-2">
                          <p className="text-xs text-surface-500 uppercase tracking-wider mb-1">
                            Error Details
                          </p>
                          <p className="text-sm text-red-400">
                            {app.error_message}
                          </p>
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button className="btn-secondary text-sm py-1.5">
                        <Eye className="w-4 h-4" />
                        View Logs
                      </button>
                      <a 
                        href={app.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-secondary text-sm py-1.5"
                      >
                        <ExternalLink className="w-4 h-4" />
                        Open Job Page
                      </a>
                      {app.status === 'failed' && (
                        <button 
                          onClick={(e) => { e.stopPropagation(); handleRetry(app.id) }}
                          className="btn-secondary text-sm py-1.5"
                        >
                          <RefreshCw className="w-4 h-4" />
                          Retry
                        </button>
                      )}
                      {app.status.startsWith('awaiting') && (
                        <button 
                          onClick={(e) => { e.stopPropagation(); handleResume(app.id) }}
                          className="btn-primary text-sm py-1.5"
                        >
                          <Play className="w-4 h-4" />
                          Resume
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
