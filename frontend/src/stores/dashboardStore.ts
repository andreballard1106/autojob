import { create } from 'zustand'
import { dashboardApi, DashboardStats, TeamMember } from '../services/api'
import { getErrorMessage } from './utils'

interface Activity {
  id: string
  action: string
  details?: Record<string, unknown>
  created_at: string
  job: {
    title: string
    company: string
    url: string
  }
  profile: string
}

interface DashboardState {
  stats: DashboardStats | null
  team: TeamMember[]
  activities: Activity[]
  chartData: Array<{ date: string; count: number }>
  isLoading: boolean
  error: string | null

  // Actions
  fetchStats: (profileId?: string, days?: number) => Promise<void>
  fetchTeam: () => Promise<void>
  fetchActivity: (limit?: number, profileId?: string) => Promise<void>
  fetchChartData: (days?: number, profileId?: string) => Promise<void>
  refreshAll: () => Promise<void>
}

export const useDashboardStore = create<DashboardState>((set, get) => ({
  stats: null,
  team: [],
  activities: [],
  chartData: [],
  isLoading: false,
  error: null,

  fetchStats: async (profileId?: string, days = 7) => {
    set({ isLoading: true, error: null })
    try {
      const stats = await dashboardApi.getStats(profileId, days)
      set({ stats, isLoading: false })
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to fetch stats'), isLoading: false })
    }
  },

  fetchTeam: async () => {
    set({ isLoading: true, error: null })
    try {
      const { team } = await dashboardApi.getTeam()
      set({ team, isLoading: false })
    } catch (error) {
      set({ error: getErrorMessage(error, 'Failed to fetch team'), isLoading: false })
    }
  },

  fetchActivity: async (limit = 50, profileId?: string) => {
    try {
      const { activities } = await dashboardApi.getActivity(limit, profileId)
      set({ activities })
    } catch (error) {
      console.error('Failed to fetch activity:', error)
    }
  },

  fetchChartData: async (days = 30, profileId?: string) => {
    try {
      const { data } = await dashboardApi.getChartData(days, profileId)
      set({ chartData: data })
    } catch (error) {
      console.error('Failed to fetch chart data:', error)
    }
  },

  refreshAll: async () => {
    const state = get()
    await Promise.all([
      state.fetchStats(),
      state.fetchTeam(),
      state.fetchActivity(),
      state.fetchChartData(),
    ])
  },
}))

