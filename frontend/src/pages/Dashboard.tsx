import { useEffect } from 'react'
import { 
  TrendingUp, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  Users,
  Briefcase,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Loader2
} from 'lucide-react'
import clsx from 'clsx'
import { useDashboardStore } from '../stores/dashboardStore'

const getStatusIcon = (action: string) => {
  if (action.includes('applied') || action.includes('success') || action.includes('confirmed')) {
    return { icon: CheckCircle, color: 'text-emerald-400', bg: 'bg-emerald-400' }
  }
  if (action.includes('error') || action.includes('failed')) {
    return { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-400' }
  }
  if (action.includes('awaiting') || action.includes('otp') || action.includes('captcha')) {
    return { icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-400' }
  }
  return { icon: Clock, color: 'text-surface-400', bg: 'bg-surface-400' }
}

export default function Dashboard() {
  const { stats, team, activities, isLoading, error, refreshAll, fetchStats, fetchTeam, fetchActivity } = useDashboardStore()

  useEffect(() => {
    // Fetch all dashboard data on mount
    fetchStats()
    fetchTeam()
    fetchActivity(10)
  }, [fetchStats, fetchTeam, fetchActivity])

  const handleRefresh = async () => {
    await refreshAll()
  }

  // Build stats array from API data
  const statsCards = stats ? [
    { 
      name: 'Total Applications', 
      value: stats.total_applications.toString(), 
      change: `${stats.recent_applications} this week`, 
      trend: 'up' as const,
      icon: Briefcase,
      color: 'primary'
    },
    { 
      name: 'Successfully Applied', 
      value: stats.by_status.applied.toString(), 
      change: `${stats.success_rate}% success rate`, 
      trend: stats.success_rate >= 50 ? 'up' as const : 'down' as const,
      icon: CheckCircle,
      color: 'emerald'
    },
    { 
      name: 'Pending', 
      value: (stats.by_status.pending + stats.by_status.in_progress).toString(), 
      change: `${stats.by_status.in_progress} in progress`, 
      trend: 'up' as const,
      icon: Clock,
      color: 'amber'
    },
    { 
      name: 'Needs Attention', 
      value: stats.by_status.awaiting_action.toString(), 
      change: `${stats.by_status.failed} failed`, 
      trend: stats.by_status.awaiting_action > 0 ? 'up' as const : 'down' as const,
      icon: AlertTriangle,
      color: 'red'
    },
  ] : []

  return (
    <div className="space-y-8 animate-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-white">Dashboard</h1>
          <p className="text-surface-400 mt-1">Monitor your job application automation</p>
        </div>
        <button 
          onClick={handleRefresh}
          disabled={isLoading}
          className="btn-secondary"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Refresh
        </button>
      </div>

      {/* Error State */}
      {error && (
        <div className="card p-4 border-red-500/50 bg-red-500/10">
          <p className="text-red-400">{error}</p>
        </div>
      )}

      {/* Stats Grid */}
      {stats ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statsCards.map((stat, index) => (
            <div 
              key={stat.name}
              className={clsx(
                "card p-6 hover:border-surface-700 transition-colors",
                `stagger-${index + 1}`
              )}
            >
              <div className="flex items-start justify-between">
                <div className={clsx(
                  "p-2.5 rounded-lg",
                  stat.color === 'primary' && "bg-primary-500/20",
                  stat.color === 'emerald' && "bg-emerald-500/20",
                  stat.color === 'amber' && "bg-amber-500/20",
                  stat.color === 'red' && "bg-red-500/20",
                )}>
                  <stat.icon className={clsx(
                    "w-5 h-5",
                    stat.color === 'primary' && "text-primary-400",
                    stat.color === 'emerald' && "text-emerald-400",
                    stat.color === 'amber' && "text-amber-400",
                    stat.color === 'red' && "text-red-400",
                  )} />
                </div>
                <div className={clsx(
                  "flex items-center gap-1 text-xs font-medium",
                  stat.trend === 'up' ? "text-emerald-400" : "text-red-400"
                )}>
                  {stat.change}
                  {stat.trend === 'up' ? (
                    <ArrowUpRight className="w-3 h-3" />
                  ) : (
                    <ArrowDownRight className="w-3 h-3" />
                  )}
                </div>
              </div>
              <div className="mt-4">
                <p className="text-3xl font-bold text-white">{stat.value}</p>
                <p className="text-sm text-surface-400 mt-1">{stat.name}</p>
              </div>
            </div>
          ))}
        </div>
      ) : isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="card p-6 animate-pulse">
              <div className="h-10 w-10 bg-surface-700 rounded-lg" />
              <div className="mt-4 h-8 w-16 bg-surface-700 rounded" />
              <div className="mt-2 h-4 w-24 bg-surface-800 rounded" />
            </div>
          ))}
        </div>
      ) : (
        <div className="card p-8 text-center">
          <p className="text-surface-400">No data available. Start by adding some job applications.</p>
        </div>
      )}

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Team Overview */}
        <div className="lg:col-span-2 card">
          <div className="p-6 border-b border-surface-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Users className="w-5 h-5 text-primary-400" />
                <h2 className="text-lg font-semibold text-white">Team Overview</h2>
              </div>
              <span className="text-sm text-surface-500">{team.length} members</span>
            </div>
          </div>
          <div className="divide-y divide-surface-800">
            {team.length > 0 ? (
              team.map((member) => (
                <div key={member.id} className="p-4 flex items-center justify-between hover:bg-surface-800/50 transition-colors">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-400 to-accent-400 flex items-center justify-center text-sm font-medium text-white">
                      {member.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div>
                      <p className="font-medium text-white">{member.name}</p>
                      <p className="text-sm text-surface-400">{member.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6 text-sm">
                    <div className="text-right">
                      <p className="font-medium text-emerald-400">{member.stats.applied}</p>
                      <p className="text-surface-500">Applied</p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium text-amber-400">{member.stats.pending}</p>
                      <p className="text-surface-500">Pending</p>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-8 text-center text-surface-500">
                No team members yet. Add profiles to get started.
              </div>
            )}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card">
          <div className="p-6 border-b border-surface-800">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-primary-400" />
              <h2 className="text-lg font-semibold text-white">Recent Activity</h2>
            </div>
          </div>
          <div className="p-4 space-y-3">
            {activities.length > 0 ? (
              activities.map((activity) => {
                const status = getStatusIcon(activity.action.toLowerCase())
                return (
                  <div 
                    key={activity.id} 
                    className="flex items-start gap-3 p-3 rounded-lg hover:bg-surface-800/50 transition-colors"
                  >
                    <div className={clsx("w-2 h-2 mt-2 rounded-full", status.bg)} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white">
                        <span className={clsx("font-medium", status.color)}>
                          {activity.action.replace(/_/g, ' ')}
                        </span>
                        {activity.job?.title && (
                          <>
                            {' • '}
                            {activity.job.title}
                          </>
                        )}
                      </p>
                      <p className="text-xs text-surface-400 mt-0.5">
                        {activity.job?.company || activity.profile} • {new Date(activity.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                )
              })
            ) : (
              <div className="p-4 text-center text-surface-500 text-sm">
                No recent activity
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
