import { useEffect, useRef, useCallback } from 'react'
import toast from 'react-hot-toast'
import { notificationsApi, SystemNotification } from '../services/api'

const POLL_INTERVAL = 10000 // 10 seconds (reduce API calls)

export function useNotificationPoller(enabled: boolean = true) {
  const lastSeenRef = useRef<string | null>(null)
  const shownNotificationsRef = useRef<Set<string>>(new Set())

  const showNotification = useCallback((notification: SystemNotification) => {
    const notificationKey = `${notification.type}-${notification.created_at}-${notification.job_id || ''}`
    
    // Skip if already shown
    if (shownNotificationsRef.current.has(notificationKey)) {
      return
    }
    
    shownNotificationsRef.current.add(notificationKey)
    
    // Keep the set from growing too large
    if (shownNotificationsRef.current.size > 100) {
      const arr = Array.from(shownNotificationsRef.current)
      shownNotificationsRef.current = new Set(arr.slice(-50))
    }

    const message = `${notification.title}: ${notification.message}`
    
    switch (notification.priority) {
      case 'urgent':
      case 'high':
        if (notification.type === 'error' || notification.type === 'job_failed') {
          toast.error(message, { 
            duration: 8000,
            style: {
              background: '#1e1e2e',
              color: '#f38ba8',
              border: '1px solid #f38ba8',
            }
          })
        } else if (notification.type === 'captcha_detected') {
          toast(message, {
            duration: 10000,
            icon: '🔒',
            style: {
              background: '#1e1e2e',
              color: '#fab387',
              border: '1px solid #fab387',
            }
          })
        } else {
          toast(message, {
            duration: 6000,
            icon: '⚠️',
            style: {
              background: '#1e1e2e',
              color: '#f9e2af',
              border: '1px solid #f9e2af',
            }
          })
        }
        break
      
      case 'normal':
        if (notification.type === 'job_completed' || notification.type === 'submit_ready') {
          toast.success(message, {
            duration: 5000,
            style: {
              background: '#1e1e2e',
              color: '#a6e3a1',
              border: '1px solid #a6e3a1',
            }
          })
        } else {
          toast(message, {
            duration: 4000,
            style: {
              background: '#1e1e2e',
              color: '#cdd6f4',
              border: '1px solid #45475a',
            }
          })
        }
        break
      
      case 'low':
      default:
        // Don't show low priority as toasts
        break
    }
  }, [])

  useEffect(() => {
    if (!enabled) return

    const pollNotifications = async () => {
      try {
        const response = await notificationsApi.getAll(20)
        
        if (response.notifications.length > 0) {
          // Find new notifications (those we haven't shown yet)
          for (const notification of response.notifications) {
            // Only show high/urgent priority notifications as toasts
            if (notification.priority === 'high' || notification.priority === 'urgent') {
              showNotification(notification)
            }
          }
          
          // Update last seen
          lastSeenRef.current = response.notifications[0].created_at
        }
      } catch {
        // Silently fail - don't spam errors for polling failures
      }
    }

    // Initial poll
    pollNotifications()

    // Set up interval
    const intervalId = setInterval(pollNotifications, POLL_INTERVAL)

    return () => clearInterval(intervalId)
  }, [enabled, showNotification])
}

export default useNotificationPoller

