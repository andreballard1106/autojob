import { create } from 'zustand'
import { Job, JobLog, jobApi } from '../services/api'
import { getErrorMessage } from './utils'

interface JobState {
  jobs: Job[]
  selectedJob: (Job & { logs?: JobLog[] }) | null
  isLoading: boolean
  error: string | null
  pagination: {
    page: number
    pageSize: number
    total: number
    totalPages: number
  }
  filters: {
    profileId?: string
    status?: string[]
  }

  // Actions
  fetchJobs: (page?: number) => Promise<void>
  fetchJob: (id: string) => Promise<void>
  createJob: (profileId: string, url: string, priority?: number) => Promise<Job>
  createBulkJobs: (profileId: string, urls: string[], priority?: number) => Promise<{
    created: number
    duplicates: number
    errors: number
  }>
  updateJob: (id: string, data: Partial<Job>) => Promise<void>
  deleteJob: (id: string) => Promise<void>
  retryJob: (id: string) => Promise<void>
  resumeJob: (id: string) => Promise<void>
  startProcessing: (profileId?: string, limit?: number) => Promise<number>
  setFilters: (filters: Partial<JobState['filters']>) => void
  setSelectedJob: (job: Job | null) => void
  updateJobStatus: (id: string, status: string) => void
  clearError: () => void
}

export const useJobStore = create<JobState>((set, get) => ({
  jobs: [],
  selectedJob: null,
  isLoading: false,
  error: null,
  pagination: {
    page: 1,
    pageSize: 20,
    total: 0,
    totalPages: 0,
  },
  filters: {},

  fetchJobs: async (page = 1) => {
    const { filters, pagination } = get()
    set({ isLoading: true, error: null })
    try {
      const result = await jobApi.list({
        profile_id: filters.profileId,
        status: filters.status,
        page,
        page_size: pagination.pageSize,
      })
      set({
        jobs: result.jobs,
        pagination: {
          page: result.page,
          pageSize: result.page_size,
          total: result.total,
          totalPages: result.total_pages,
        },
        isLoading: false,
      })
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to fetch jobs'), isLoading: false })
    }
  },

  fetchJob: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      const job = await jobApi.get(id)
      set({ selectedJob: job, isLoading: false })
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to fetch job'), isLoading: false })
    }
  },

  createJob: async (profileId: string, url: string, priority = 0) => {
    set({ isLoading: true, error: null })
    try {
      const job = await jobApi.create({ profile_id: profileId, url, priority })
      set((state) => ({ jobs: [job, ...state.jobs], isLoading: false }))
      return job
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to create job'), isLoading: false })
      throw error
    }
  },

  createBulkJobs: async (profileId: string, urls: string[], priority = 0) => {
    set({ isLoading: true, error: null })
    try {
      const result = await jobApi.createBulk({ profile_id: profileId, urls, priority })
      await get().fetchJobs()
      set({ isLoading: false })
      return result
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to create jobs'), isLoading: false })
      throw error
    }
  },

  updateJob: async (id: string, data: Partial<Job>) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await jobApi.update(id, data)
      set((state) => ({
        jobs: state.jobs.map((j) => (j.id === id ? updated : j)),
        selectedJob: state.selectedJob?.id === id
          ? { ...state.selectedJob, ...updated }
          : state.selectedJob,
        isLoading: false,
      }))
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to update job'), isLoading: false })
      throw error
    }
  },

  deleteJob: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      await jobApi.delete(id)
      set((state) => ({
        jobs: state.jobs.filter((j) => j.id !== id),
        selectedJob: state.selectedJob?.id === id ? null : state.selectedJob,
        isLoading: false,
      }))
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to delete job'), isLoading: false })
      throw error
    }
  },

  retryJob: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await jobApi.retry(id)
      set((state) => ({ jobs: state.jobs.map((j) => (j.id === id ? updated : j)), isLoading: false }))
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to retry job'), isLoading: false })
      throw error
    }
  },

  resumeJob: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await jobApi.resume(id)
      set((state) => ({ jobs: state.jobs.map((j) => (j.id === id ? updated : j)), isLoading: false }))
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to resume job'), isLoading: false })
      throw error
    }
  },

  startProcessing: async (profileId?: string, limit = 10) => {
    set({ isLoading: true, error: null })
    try {
      const result = await jobApi.startProcessing(profileId, limit)
      await get().fetchJobs()
      set({ isLoading: false })
      return result.queued
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to start processing'), isLoading: false })
      throw error
    }
  },

  setFilters: (filters) => {
    set((state) => ({
      filters: { ...state.filters, ...filters },
    }))
  },

  setSelectedJob: (job) => {
    set({ selectedJob: job })
  },

  // For WebSocket updates
  updateJobStatus: (id: string, status: string) => {
    set((state) => ({
      jobs: state.jobs.map((j) =>
        j.id === id ? { ...j, status } : j
      ),
      selectedJob: state.selectedJob?.id === id
        ? { ...state.selectedJob, status }
        : state.selectedJob,
    }))
  },

  clearError: () => {
    set({ error: null })
  },
}))

