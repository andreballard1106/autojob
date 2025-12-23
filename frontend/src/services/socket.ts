/**
 * WebSocket Service
 * 
 * Provides a singleton WebSocket connection for real-time updates.
 */

type MessageHandler = (data: unknown) => void

class SocketService {
  private ws: WebSocket | null = null
  private handlers: Map<string, Set<MessageHandler>> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 3000
  private isConnecting = false

  /**
   * Connect to WebSocket server
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return
    }

    this.isConnecting = true

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const url = `${protocol}//${host}/ws`

    console.log('Connecting to WebSocket:', url)

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.isConnecting = false
      this.reconnectAttempts = 0
      this.emit('connected', {})
    }

    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      this.isConnecting = false
      this.ws = null
      this.emit('disconnected', {})

      // Attempt reconnection
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        console.log(`Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts})`)
        setTimeout(() => this.connect(), this.reconnectDelay)
      }
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      this.emit('error', { error })
    }

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        const type = data.type || 'message'
        this.emit(type, data)
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * Send a message to the server
   */
  send(type: string, payload: Record<string, unknown> = {}): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...payload }))
    } else {
      console.warn('WebSocket not connected, cannot send message')
    }
  }

  /**
   * Subscribe to a profile for targeted updates
   */
  subscribeToProfile(profileId: string): void {
    this.send('subscribe:profile', { profile_id: profileId })
  }

  /**
   * Resume a paused job
   */
  resumeJob(jobId: string): void {
    this.send('job:resume', { job_id: jobId })
  }

  /**
   * Register a handler for a specific event type
   */
  on(type: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set())
    }
    this.handlers.get(type)!.add(handler)

    // Return unsubscribe function
    return () => {
      this.handlers.get(type)?.delete(handler)
    }
  }

  /**
   * Emit an event to all registered handlers
   */
  private emit(type: string, data: unknown): void {
    this.handlers.get(type)?.forEach((handler) => handler(data))
    // Also emit to 'message' handlers for all events
    if (type !== 'message') {
      this.handlers.get('message')?.forEach((handler) => handler(data))
    }
  }

  /**
   * Check if connected
   */
  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

// Singleton instance
export const socketService = new SocketService()
export default socketService

