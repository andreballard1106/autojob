import { useState, useEffect } from 'react'
import { 
  Plus, 
  Search,
  Upload,
  Play,
  RotateCcw,
  ExternalLink,
  Trash2,
  Filter,
  CheckCircle,
  Clock,
  AlertTriangle,
  XCircle,
  Loader2,
  Eye,
  History,
  X,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'
import { useJobStore } from '../stores/jobStore'
import { useProfileStore } from '../stores/profileStore'
import { JOB_STATUS_CONFIG, JobStatus, Job } from '../types'
import { jobApi } from '../services/api'

const statusIcons = {
  pending: Clock,
  queued: Clock,
  in_progress: Play,
  awaiting_otp: AlertTriangle,
  awaiting_captcha: AlertTriangle,
  awaiting_user: AlertTriangle,
  awaiting_action: AlertTriangle,
  submitted: Clock,
  applied: CheckCircle,
  failed: XCircle,
  cancelled: XCircle,
  duplicate: XCircle,
}

const colorToClass: Record<string, string> = {
  success: 'badge-success',
  warning: 'badge-warning',
  error: 'badge-error',
  info: 'badge-info',
  neutral: 'badge-neutral',
}

function getStatusConfig(status: string) {
  const config = JOB_STATUS_CONFIG[status as JobStatus] || JOB_STATUS_CONFIG.pending
  const Icon = statusIcons[status as JobStatus] || Clock
  return {
    label: config.label,
    icon: Icon,
    className: colorToClass[config.color] || 'badge-neutral',
  }
}

interface JobDetailData {
  job: {
    id: string
    url: string
    company_name?: string
    job_title?: string
    status: string
    error_message?: string
    profile_name: string
    created_at: string
    updated_at: string
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
}

export default function Jobs() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [newUrls, setNewUrls] = useState('')
  const [selectedProfileId, setSelectedProfileId] = useState('')
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [jobDetail, setJobDetail] = useState<JobDetailData | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    history: true,
    autofill: false,
    pages: false,
  })

  const { 
    jobs, 
    isLoading, 
    error,
    pagination,
    fetchJobs, 
    createBulkJobs, 
    deleteJob, 
    retryJob,
    resumeJob,
    startProcessing,
    clearError
  } = useJobStore()

  const { profiles, fetchProfiles } = useProfileStore()

  useEffect(() => {
    fetchJobs()
    fetchProfiles()
  }, [fetchJobs, fetchProfiles])

  const filteredJobs = jobs.filter(job =>
    (job.company_name?.toLowerCase().includes(searchQuery.toLowerCase()) || false) ||
    (job.job_title?.toLowerCase().includes(searchQuery.toLowerCase()) || false) ||
    job.url.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleAddJobs = async () => {
    if (!selectedProfileId) {
      toast.error('Please select a profile')
      return
    }
    const urls = newUrls.split('\n').filter(u => u.trim())
    if (urls.length === 0) {
      toast.error('Please enter at least one URL')
      return
    }
    try {
      const result = await createBulkJobs(selectedProfileId, urls)
      toast.success(`Added ${result.created} jobs. ${result.duplicates} duplicates skipped.`)
      setShowAddModal(false)
      setNewUrls('')
    } catch {
      toast.error('Failed to add jobs')
    }
  }

  const handleStartProcessing = async () => {
    try {
      const count = await startProcessing(undefined, 10)
      toast.success(`Started processing ${count} jobs`)
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { detail?: string } } }
      const message = axiosError?.response?.data?.detail || 'Failed to start processing'
      toast.error(message)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteJob(id)
      toast.success('Job removed')
    } catch {
      toast.error('Failed to delete job')
    }
  }

  const handleRetry = async (id: string) => {
    try {
      await retryJob(id)
      toast.success('Job queued for retry')
    } catch {
      toast.error('Failed to retry job')
    }
  }

  const handleResume = async (id: string) => {
    try {
      await resumeJob(id)
      toast.success('Job resumed')
    } catch {
      toast.error('Failed to resume job')
    }
  }

  const handleViewJob = async (job: Job) => {
    setSelectedJob(job)
    setLoadingDetail(true)
    try {
      const detail = await jobApi.getDetail(job.id)
      setJobDetail(detail)
    } catch {
      toast.error('Failed to load job details')
    } finally {
      setLoadingDetail(false)
    }
  }

  const closeJobDetail = () => {
    setSelectedJob(null)
    setJobDetail(null)
  }

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  const formatActionLabel = (action: string): string => {
    return action
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase())
  }

  const getActionColor = (action: string): string => {
    if (action.includes('error') || action.includes('failed')) return 'text-red-400'
    if (action.includes('captcha')) return 'text-amber-400'
    if (action.includes('completed') || action.includes('filled') || action.includes('ready')) return 'text-emerald-400'
    if (action.includes('started') || action.includes('loaded')) return 'text-primary-400'
    return 'text-surface-300'
  }

  // Calculate stats
  const statsData = [
    { label: 'Total', count: pagination.total, color: 'text-white' },
    { label: 'Pending', count: jobs.filter(j => j.status === 'pending' || j.status === 'queued').length, color: 'text-surface-400' },
    { label: 'In Progress', count: jobs.filter(j => j.status === 'in_progress').length, color: 'text-primary-400' },
    { label: 'Applied', count: jobs.filter(j => j.status === 'applied').length, color: 'text-emerald-400' },
    { label: 'Needs Action', count: jobs.filter(j => j.status.startsWith('awaiting')).length, color: 'text-amber-400' },
  ]

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">Job Queue</h1>
          <p className="text-surface-400 mt-1">Manage and track job applications</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary">
            <Upload className="w-4 h-4" />
            Import CSV
          </button>
          <button 
            onClick={() => setShowAddModal(true)}
            className="btn-primary"
          >
            <Plus className="w-4 h-4" />
            Add Jobs
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="card p-4 border-red-500/50 bg-red-500/10 flex justify-between items-center">
          <p className="text-red-400">{error}</p>
          <button onClick={clearError} className="text-red-400 hover:text-red-300">Dismiss</button>
        </div>
      )}

      {/* Filters and Search */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-surface-500" />
          <input
            type="text"
            placeholder="Search jobs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-12"
          />
        </div>
        <button className="btn-secondary">
          <Filter className="w-4 h-4" />
          Filter
        </button>
        <button 
          onClick={handleStartProcessing}
          disabled={isLoading}
          className="btn-primary"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          Start Processing
        </button>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        {statsData.map((stat) => (
          <div key={stat.label} className="card p-4 text-center">
            <p className={clsx("text-2xl font-bold", stat.color)}>{stat.count}</p>
            <p className="text-xs text-surface-500">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Jobs Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-surface-800 bg-surface-800/50">
                <th className="text-left text-xs font-medium text-surface-400 uppercase tracking-wider px-6 py-4">
                  Job
                </th>
                <th className="text-left text-xs font-medium text-surface-400 uppercase tracking-wider px-6 py-4">
                  Profile
                </th>
                <th className="text-left text-xs font-medium text-surface-400 uppercase tracking-wider px-6 py-4">
                  Status
                </th>
                <th className="text-left text-xs font-medium text-surface-400 uppercase tracking-wider px-6 py-4">
                  Created
                </th>
                <th className="text-right text-xs font-medium text-surface-400 uppercase tracking-wider px-6 py-4">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-800">
              {isLoading && jobs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary-400" />
                    <p className="mt-2 text-surface-400">Loading jobs...</p>
                  </td>
                </tr>
              ) : filteredJobs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-surface-400">
                    No jobs found. Add some job URLs to get started.
                  </td>
                </tr>
              ) : (
                filteredJobs.map((job) => {
                  const status = getStatusConfig(job.status)
                  const profileName = profiles.find(p => p.id === job.profile_id)?.name || 'Unknown'
                  return (
                    <tr key={job.id} className="hover:bg-surface-800/50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 rounded-lg bg-surface-800 flex items-center justify-center flex-shrink-0">
                            <span className="text-xs font-bold text-surface-400">
                              {(job.company_name || job.url).slice(0, 2).toUpperCase()}
                            </span>
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium text-white truncate">
                              {job.job_title || 'Untitled Position'}
                            </p>
                            <p className="text-sm text-surface-400">
                              {job.company_name || new URL(job.url).hostname}
                            </p>
                            <a 
                              href={job.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-primary-400 hover:text-primary-300 flex items-center gap-1 mt-1"
                            >
                              View Job <ExternalLink className="w-3 h-3" />
                            </a>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-sm text-surface-300">{profileName}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={status.className}>
                          <status.icon className="w-3 h-3 mr-1" />
                          {status.label}
                        </span>
                        {job.error_message && (
                          <p className="text-xs text-red-400 mt-1 max-w-xs truncate">
                            {job.error_message}
                          </p>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-surface-400">
                        {new Date(job.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-end gap-2">
                          <button 
                            onClick={() => handleViewJob(job)}
                            className="p-2 rounded-lg text-surface-400 hover:text-primary-400 hover:bg-primary-500/20"
                            title="View Details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          {job.status === 'failed' && (
                            <button 
                              onClick={() => handleRetry(job.id)}
                              className="p-2 rounded-lg text-surface-400 hover:text-white hover:bg-surface-800"
                              title="Retry"
                            >
                              <RotateCcw className="w-4 h-4" />
                            </button>
                          )}
                          {job.status.startsWith('awaiting') && (
                            <button 
                              onClick={() => handleResume(job.id)}
                              className="p-2 rounded-lg text-amber-400 hover:text-amber-300 hover:bg-amber-500/20"
                              title="Resume"
                            >
                              <Play className="w-4 h-4" />
                            </button>
                          )}
                          <button 
                            onClick={() => handleDelete(job.id)}
                            className="p-2 rounded-lg text-surface-400 hover:text-red-400 hover:bg-red-500/20"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Jobs Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-lg animate-slide-up">
            <div className="p-6 border-b border-surface-800">
              <h2 className="text-xl font-semibold text-white">Add Jobs to Queue</h2>
              <p className="text-sm text-surface-400 mt-1">
                Enter job URLs, one per line
              </p>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="label">Profile</label>
                <select 
                  value={selectedProfileId}
                  onChange={(e) => setSelectedProfileId(e.target.value)}
                  className="input"
                >
                  <option value="">Select a profile...</option>
                  {profiles.map((profile) => (
                    <option key={profile.id} value={profile.id}>
                      {profile.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label">Job URLs</label>
                <textarea
                  value={newUrls}
                  onChange={(e) => setNewUrls(e.target.value)}
                  placeholder="https://linkedin.com/jobs/view/123456&#10;https://indeed.com/job/789012&#10;..."
                  rows={6}
                  className="input font-mono text-sm"
                />
                <p className="text-xs text-surface-500 mt-2">
                  {newUrls.split('\n').filter(u => u.trim()).length} URLs entered
                </p>
              </div>
            </div>
            <div className="p-6 border-t border-surface-800 flex justify-end gap-3">
              <button 
                onClick={() => setShowAddModal(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button 
                onClick={handleAddJobs}
                disabled={isLoading}
                className="btn-primary"
              >
                {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                Add {newUrls.split('\n').filter(u => u.trim()).length} Jobs
              </button>
            </div>
          </div>
        </div>
      )}

      {selectedJob && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-4xl max-h-[90vh] overflow-hidden animate-slide-up flex flex-col">
            <div className="p-6 border-b border-surface-800 flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">
                  {jobDetail?.job.job_title || selectedJob.job_title || 'Job Details'}
                </h2>
                <p className="text-sm text-surface-400 mt-1">
                  {jobDetail?.job.company_name || selectedJob.company_name || new URL(selectedJob.url).hostname}
                </p>
              </div>
              <button
                onClick={closeJobDetail}
                className="p-2 rounded-lg text-surface-400 hover:text-white hover:bg-surface-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {loadingDetail ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                </div>
              ) : jobDetail ? (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="card p-4 text-center">
                      <p className="text-2xl font-bold text-primary-400">
                        {jobDetail.history.length}
                      </p>
                      <p className="text-xs text-surface-500">Total Actions</p>
                    </div>
                    <div className="card p-4 text-center">
                      <p className="text-2xl font-bold text-emerald-400">
                        {jobDetail.autofill_results.filter(r => r.success).length}
                      </p>
                      <p className="text-xs text-surface-500">Fields Filled</p>
                    </div>
                    <div className="card p-4 text-center">
                      <p className="text-2xl font-bold text-red-400">
                        {jobDetail.autofill_results.filter(r => !r.success).length}
                      </p>
                      <p className="text-xs text-surface-500">Fields Failed</p>
                    </div>
                    <div className="card p-4 text-center">
                      <p className="text-2xl font-bold text-amber-400">
                        {jobDetail.page_snapshots.length}
                      </p>
                      <p className="text-xs text-surface-500">Pages Processed</p>
                    </div>
                  </div>

                  <div className="card overflow-hidden">
                    <button
                      onClick={() => toggleSection('history')}
                      className="w-full p-4 flex items-center justify-between text-left hover:bg-surface-800/50"
                    >
                      <div className="flex items-center gap-2">
                        <History className="w-5 h-5 text-primary-400" />
                        <span className="font-medium text-white">Activity History</span>
                        <span className="text-xs text-surface-500">({jobDetail.history.length})</span>
                      </div>
                      {expandedSections.history ? (
                        <ChevronUp className="w-5 h-5 text-surface-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-surface-400" />
                      )}
                    </button>
                    {expandedSections.history && (
                      <div className="border-t border-surface-800 max-h-64 overflow-y-auto">
                        {jobDetail.history.length === 0 ? (
                          <p className="p-4 text-center text-surface-500">No activity recorded yet</p>
                        ) : (
                          <div className="divide-y divide-surface-800">
                            {jobDetail.history.map((log) => (
                              <div key={log.id} className="p-3 hover:bg-surface-800/30">
                                <div className="flex items-start justify-between">
                                  <span className={clsx("font-medium text-sm", getActionColor(log.action))}>
                                    {formatActionLabel(log.action)}
                                  </span>
                                  <span className="text-xs text-surface-500">
                                    {new Date(log.created_at).toLocaleString()}
                                  </span>
                                </div>
                                {log.details && Object.keys(log.details).length > 0 && (
                                  <div className="mt-1 text-xs text-surface-400">
                                    {Object.entries(log.details).slice(0, 3).map(([key, value]) => (
                                      <span key={key} className="mr-3">
                                        <span className="text-surface-500">{key}:</span>{' '}
                                        {typeof value === 'string' ? value.slice(0, 50) : String(value)}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="card overflow-hidden">
                    <button
                      onClick={() => toggleSection('autofill')}
                      className="w-full p-4 flex items-center justify-between text-left hover:bg-surface-800/50"
                    >
                      <div className="flex items-center gap-2">
                        <CheckCircle className="w-5 h-5 text-emerald-400" />
                        <span className="font-medium text-white">Autofill Results</span>
                        <span className="text-xs text-surface-500">({jobDetail.autofill_results.length})</span>
                      </div>
                      {expandedSections.autofill ? (
                        <ChevronUp className="w-5 h-5 text-surface-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-surface-400" />
                      )}
                    </button>
                    {expandedSections.autofill && (
                      <div className="border-t border-surface-800 max-h-64 overflow-y-auto">
                        {jobDetail.autofill_results.length === 0 ? (
                          <p className="p-4 text-center text-surface-500">No autofill results yet</p>
                        ) : (
                          <div className="divide-y divide-surface-800">
                            {jobDetail.autofill_results.map((result, idx) => (
                              <div key={idx} className="p-3 hover:bg-surface-800/30 flex items-start justify-between">
                                <div>
                                  <span className={clsx(
                                    "font-medium text-sm",
                                    result.success ? "text-emerald-400" : "text-red-400"
                                  )}>
                                    {result.field_name || result.selector.slice(0, 30)}
                                  </span>
                                  <p className="text-xs text-surface-500 mt-0.5">{result.action}</p>
                                </div>
                                {result.error && (
                                  <span className="text-xs text-red-400 max-w-xs truncate">{result.error}</span>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="card overflow-hidden">
                    <button
                      onClick={() => toggleSection('pages')}
                      className="w-full p-4 flex items-center justify-between text-left hover:bg-surface-800/50"
                    >
                      <div className="flex items-center gap-2">
                        <ExternalLink className="w-5 h-5 text-amber-400" />
                        <span className="font-medium text-white">Page Snapshots</span>
                        <span className="text-xs text-surface-500">({jobDetail.page_snapshots.length})</span>
                      </div>
                      {expandedSections.pages ? (
                        <ChevronUp className="w-5 h-5 text-surface-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-surface-400" />
                      )}
                    </button>
                    {expandedSections.pages && (
                      <div className="border-t border-surface-800 max-h-64 overflow-y-auto">
                        {jobDetail.page_snapshots.length === 0 ? (
                          <p className="p-4 text-center text-surface-500">No pages processed yet</p>
                        ) : (
                          <div className="divide-y divide-surface-800">
                            {jobDetail.page_snapshots.map((page, idx) => (
                              <div key={idx} className="p-3 hover:bg-surface-800/30">
                                <div className="flex items-start justify-between">
                                  <div>
                                    <span className="font-medium text-sm text-white">
                                      Page {page.page_number}: {page.title || 'Untitled'}
                                    </span>
                                    <p className="text-xs text-surface-500 mt-0.5 truncate max-w-md">{page.url}</p>
                                  </div>
                                  <div className="text-right text-xs text-surface-400">
                                    <p>{page.inputs_count} inputs</p>
                                    <p>{page.buttons_count} buttons</p>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </>
              ) : (
                <p className="text-center text-surface-500">Failed to load job details</p>
              )}
            </div>

            <div className="p-6 border-t border-surface-800 flex justify-between">
              <a
                href={selectedJob.url}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-secondary"
              >
                <ExternalLink className="w-4 h-4" />
                Open Job Page
              </a>
              <div className="flex gap-2">
                {selectedJob.status === 'failed' && (
                  <button
                    onClick={() => {
                      handleRetry(selectedJob.id)
                      closeJobDetail()
                    }}
                    className="btn-secondary"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Retry
                  </button>
                )}
                {selectedJob.status.startsWith('awaiting') && (
                  <button
                    onClick={() => {
                      handleResume(selectedJob.id)
                      closeJobDetail()
                    }}
                    className="btn-primary"
                  >
                    <Play className="w-4 h-4" />
                    Resume
                  </button>
                )}
                <button onClick={closeJobDetail} className="btn-secondary">
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
