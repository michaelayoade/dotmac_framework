'use client'

import { useState, useEffect } from 'react'
import { X, MessageCircle, Send, MinusCircle } from 'lucide-react'

interface ChatMessage {
  id: string
  content: string
  sender: 'user' | 'agent' | 'system'
  timestamp: Date
  senderName?: string
}

interface LiveChatWidgetProps {
  department?: 'sales' | 'support'
  position?: 'bottom-right' | 'bottom-left'
  triggerText?: string
}

export function LiveChatWidget({ 
  department = 'sales', 
  position = 'bottom-right',
  triggerText = 'Chat with Sales'
}: LiveChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [currentMessage, setCurrentMessage] = useState('')
  const [customerInfo, setCustomerInfo] = useState({
    name: '',
    email: '',
    company: '',
    hasProvided: false
  })
  const [agentInfo, setAgentInfo] = useState({
    name: '',
    status: 'offline' as 'online' | 'busy' | 'offline'
  })

  // Initialize chat when opened
  useEffect(() => {
    if (isOpen && !isConnected) {
      initializeChat()
    }
  }, [isOpen, isConnected])

  const initializeChat = async () => {
    try {
      // Connect to existing LiveChatPlugin WebSocket
      const response = await fetch('/api/chat/initialize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          department,
          page_url: window.location.href,
          user_agent: navigator.userAgent,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        setIsConnected(true)
        
        // Add welcome message
        setMessages([{
          id: 'welcome',
          content: `Hi! I'm here to help you learn more about DotMac Platform. How can I assist you today?`,
          sender: 'system',
          timestamp: new Date()
        }])

        // Set agent info if available
        if (data.agent) {
          setAgentInfo({
            name: data.agent.name,
            status: data.agent.status
          })
        }
      }
    } catch (error) {
      console.error('Failed to initialize chat:', error)
      // Fallback to demo mode
      setMessages([{
        id: 'offline',
        content: `Thanks for your interest in DotMac Platform! Our sales team is currently offline, but you can leave a message and we'll get back to you soon.`,
        sender: 'system',
        timestamp: new Date()
      }])
    }
  }

  const handleSendMessage = async () => {
    if (!currentMessage.trim()) return

    const newMessage: ChatMessage = {
      id: Date.now().toString(),
      content: currentMessage,
      sender: 'user',
      timestamp: new Date(),
      senderName: customerInfo.name || 'You'
    }

    setMessages(prev => [...prev, newMessage])
    setCurrentMessage('')

    // Send to backend
    try {
      await fetch('/api/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          content: currentMessage,
          session_id: 'demo-session', // Would be actual session ID
          sender_info: customerInfo
        }),
      })

      // Simulate agent response for demo
      setTimeout(() => {
        const agentResponse: ChatMessage = {
          id: (Date.now() + 1).toString(),
          content: getAgentResponse(currentMessage),
          sender: 'agent',
          timestamp: new Date(),
          senderName: agentInfo.name || 'Sales Agent'
        }
        setMessages(prev => [...prev, agentResponse])
      }, 1500)

    } catch (error) {
      console.error('Failed to send message:', error)
    }
  }

  const getAgentResponse = (userMessage: string): string => {
    const msg = userMessage.toLowerCase()
    
    if (msg.includes('price') || msg.includes('cost') || msg.includes('pricing')) {
      return "Our pricing starts at $49/month for the Starter plan. Would you like me to show you a detailed breakdown of what's included?"
    }
    
    if (msg.includes('demo') || msg.includes('trial')) {
      return "Great! We offer a 14-day free trial with full access to all features. I can set that up for you right now - just need a few details."
    }
    
    if (msg.includes('feature') || msg.includes('what') || msg.includes('do')) {
      return "DotMac Platform offers complete ISP management including network automation, customer portal, billing, and plugin-based extensions. What specific area interests you most?"
    }
    
    return "That's a great question! Let me connect you with one of our ISP specialists who can provide detailed information. Can you share your company name and email?"
  }

  const handleCustomerInfoSubmit = () => {
    if (customerInfo.name && customerInfo.email) {
      setCustomerInfo(prev => ({ ...prev, hasProvided: true }))
      
      const infoMessage: ChatMessage = {
        id: 'info-provided',
        content: `Thanks ${customerInfo.name}! I've noted your information. How can I help you with DotMac Platform today?`,
        sender: 'agent',
        timestamp: new Date(),
        senderName: 'Sales Agent'
      }
      setMessages(prev => [...prev, infoMessage])
    }
  }

  const positionClasses = position === 'bottom-right' 
    ? 'bottom-4 right-4' 
    : 'bottom-4 left-4'

  return (
    <div className={`fixed ${positionClasses} z-50`}>
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-full shadow-lg flex items-center space-x-2 transition-all duration-300 hover:shadow-xl"
        >
          <MessageCircle className="w-5 h-5" />
          <span className="font-medium">{triggerText}</span>
        </button>
      )}

      {isOpen && (
        <div className="bg-white rounded-lg shadow-2xl w-80 h-96 flex flex-col border border-gray-200">
          {/* Header */}
          <div className="bg-purple-600 text-white p-4 rounded-t-lg flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-400 rounded-full"></div>
              <div>
                <h3 className="font-semibold">Sales Chat</h3>
                <p className="text-xs text-purple-100">
                  {isConnected ? 'Connected' : 'Connecting...'}
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-purple-200 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3">
            {!customerInfo.hasProvided && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 space-y-2">
                <p className="text-sm font-medium text-purple-800">Quick Start</p>
                <div className="space-y-2">
                  <input
                    type="text"
                    placeholder="Your name"
                    value={customerInfo.name}
                    onChange={(e) => setCustomerInfo(prev => ({ ...prev, name: e.target.value }))}
                    className="w-full px-3 py-1 border border-purple-200 rounded text-sm focus:ring-1 focus:ring-purple-500 focus:border-purple-500"
                  />
                  <input
                    type="email"
                    placeholder="Your email"
                    value={customerInfo.email}
                    onChange={(e) => setCustomerInfo(prev => ({ ...prev, email: e.target.value }))}
                    className="w-full px-3 py-1 border border-purple-200 rounded text-sm focus:ring-1 focus:ring-purple-500 focus:border-purple-500"
                  />
                  <input
                    type="text"
                    placeholder="Company name (optional)"
                    value={customerInfo.company}
                    onChange={(e) => setCustomerInfo(prev => ({ ...prev, company: e.target.value }))}
                    className="w-full px-3 py-1 border border-purple-200 rounded text-sm focus:ring-1 focus:ring-purple-500 focus:border-purple-500"
                  />
                  <button
                    onClick={handleCustomerInfoSubmit}
                    className="w-full bg-purple-600 text-white py-1 rounded text-sm font-medium hover:bg-purple-700 transition-colors"
                  >
                    Start Chat
                  </button>
                </div>
              </div>
            )}

            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs px-3 py-2 rounded-lg text-sm ${
                    message.sender === 'user'
                      ? 'bg-purple-600 text-white'
                      : message.sender === 'system'
                      ? 'bg-gray-100 text-gray-700'
                      : 'bg-gray-200 text-gray-800'
                  }`}
                >
                  <p>{message.content}</p>
                  <p className={`text-xs mt-1 ${
                    message.sender === 'user' ? 'text-purple-200' : 'text-gray-500'
                  }`}>
                    {message.timestamp.toLocaleTimeString([], { 
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="p-4 border-t border-gray-200">
            <div className="flex space-x-2">
              <input
                type="text"
                value={currentMessage}
                onChange={(e) => setCurrentMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
                placeholder="Type your message..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-1 focus:ring-purple-500 focus:border-purple-500"
              />
              <button
                onClick={handleSendMessage}
                disabled={!currentMessage.trim()}
                className="bg-purple-600 text-white px-3 py-2 rounded-md hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}