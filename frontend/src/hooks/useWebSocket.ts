import { useEffect, useCallback, useState } from 'react'
import toast from 'react-hot-toast'
import { socketService } from '../services/socket'

interface WebSocketMessage {
  type: string
  [key: string]: unknown
}

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void
  onStatusChange?: (jobId: string, status: string) => void
  onInterventionNeeded?: (jobId: string, challengeType: string) => void
}

interface UseWebSocketReturn {
  isConnected: boolean
  subscribeToProfile: (profileId: string) => void
  resumeJob: (jobId: string) => void
  sendMessage: (message: WebSocketMessage) => void
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { onMessage, onStatusChange, onInterventionNeeded } = options
  const [isConnected, setIsConnected] = useState(socketService.isConnected)

  useEffect(() => {
    socketService.connect()

    const unsubConnected = socketService.on('connected', () => {
      setIsConnected(true)
    })

    const unsubDisconnected = socketService.on('disconnected', () => {
      setIsConnected(false)
    })

    const unsubStatusChanged = socketService.on('job_status_changed', (data) => {
      const msg = data as WebSocketMessage
      if (onStatusChange) {
        onStatusChange(msg.job_id as string, msg.new_status as string)
      }
    })

    const unsubIntervention = socketService.on('intervention_needed', (data) => {
      const msg = data as WebSocketMessage
      if (onInterventionNeeded) {
        onInterventionNeeded(msg.job_id as string, msg.challenge_type as string)
      }
      toast(`Action required: ${msg.challenge_type} for ${msg.job_title || 'job'}`, {
        icon: '!',
        duration: 10000,
      })
    })

    const unsubCompleted = socketService.on('job_completed', (data) => {
      const msg = data as WebSocketMessage
      toast.success(
        `Applied to ${msg.job_title || 'job'} at ${msg.company_name || 'company'}!`
      )
    })

    const unsubNotification = socketService.on('notification', (data) => {
      const msg = data as WebSocketMessage
      const notifType = msg.notification_type as string
      if (notifType === 'success') {
        toast.success(msg.message as string)
      } else if (notifType === 'error') {
        toast.error(msg.message as string)
      } else if (notifType === 'warning') {
        toast(msg.message as string, { icon: '!' })
      } else {
        toast(msg.message as string)
      }
    })

    const unsubMessage = onMessage
      ? socketService.on('message', (data) => onMessage(data as WebSocketMessage))
      : undefined

    return () => {
      unsubConnected()
      unsubDisconnected()
      unsubStatusChanged()
      unsubIntervention()
      unsubCompleted()
      unsubNotification()
      unsubMessage?.()
    }
  }, [onMessage, onStatusChange, onInterventionNeeded])

  const sendMessage = useCallback((message: WebSocketMessage) => {
    socketService.send(message.type, message)
  }, [])

  const subscribeToProfile = useCallback((profileId: string) => {
    socketService.subscribeToProfile(profileId)
  }, [])

  const resumeJob = useCallback((jobId: string) => {
    socketService.resumeJob(jobId)
    toast.success('Resuming job...')
  }, [])

  return {
    isConnected,
    subscribeToProfile,
    resumeJob,
    sendMessage,
  }
}

export default useWebSocket
