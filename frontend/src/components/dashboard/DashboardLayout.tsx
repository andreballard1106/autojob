import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  Users, 
  Briefcase, 
  FileText, 
  Settings,
  Bell,
  Menu,
  X,
  Zap
} from 'lucide-react'
import { useState } from 'react'
import clsx from 'clsx'
import { useNotificationPoller } from '../../hooks/useNotificationPoller'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Profiles', href: '/profiles', icon: Users },
  { name: 'Jobs', href: '/jobs', icon: Briefcase },
  { name: 'Applications', href: '/applications', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export default function DashboardLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()
  
  // Poll for notifications and show them as toasts
  useNotificationPoller(true)

  return (
    <div className="min-h-screen bg-surface-950">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={clsx(
        "fixed inset-y-0 left-0 z-50 w-64 bg-surface-900 border-r border-surface-800",
        "transform transition-transform duration-300 ease-in-out lg:translate-x-0",
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      )}>
        {/* Logo */}
        <div className="h-16 flex items-center gap-3 px-6 border-b border-surface-800">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="font-display font-semibold text-lg text-white">
            JobAuto
          </span>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={() => setSidebarOpen(false)}
                className={clsx(
                  "flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200",
                  "text-sm font-medium",
                  isActive 
                    ? "bg-primary-600/20 text-primary-400 border border-primary-500/30" 
                    : "text-surface-400 hover:text-white hover:bg-surface-800"
                )}
              >
                <item.icon className="w-5 h-5" />
                {item.name}
              </NavLink>
            )
          })}
        </nav>

        {/* Bottom section */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-surface-800">
          <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-surface-800/50">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-400 to-accent-400" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate">Team Admin</p>
              <p className="text-xs text-surface-500 truncate">admin@company.com</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-16 bg-surface-950/80 backdrop-blur-lg border-b border-surface-800">
          <div className="flex items-center justify-between h-full px-4 lg:px-8">
            {/* Mobile menu button */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 rounded-lg text-surface-400 hover:text-white hover:bg-surface-800 lg:hidden"
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            {/* Page title - could be dynamic */}
            <h1 className="text-lg font-semibold text-white hidden lg:block">
              {navigation.find(n => n.href === location.pathname)?.name || 'Dashboard'}
            </h1>

            {/* Right section */}
            <div className="flex items-center gap-4">
              {/* Notifications */}
              <button className="relative p-2 rounded-lg text-surface-400 hover:text-white hover:bg-surface-800">
                <Bell className="w-5 h-5" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-accent-500 rounded-full" />
              </button>

              {/* Status indicator */}
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30">
                <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                <span className="text-xs font-medium text-emerald-400">System Online</span>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

