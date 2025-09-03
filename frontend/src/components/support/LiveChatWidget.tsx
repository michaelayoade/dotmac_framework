/**
 * Live Chat Widget Component
 * Real-time chat interface with WebSocket connection
 */

'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  MessageCircle,
  X,
  Send,
  Minimize2,
  Maximize2,
  Paperclip,
  User,
  Bot,
  Clock,
  CheckCircle2,
  AlertCircle,
  Smile,
} from 'lucide-react';

// Leverage existing DotMac UI components
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';

// Types
interface ChatMessage {
  id: string;
  type: 'message' | 'system' | 'agent_join' | 'agent_leave' | 'typing';
  content: string;
  sender_type: 'customer' | 'agent' | 'system';
  sender_name: string;
  sender_id?: string;
  timestamp: string;
  delivered?: boolean;
  read?: boolean;
}

interface ChatSession {
  id: string;
  session_id: string;
  status: 'waiting' | 'active' | 'ended';
  assigned_agent_name?: string;
  created_at: string;
  wait_time_seconds?: number;
}

interface ChatWidgetProps {
  customerId?: string;
  customerName?: string;
  customerEmail?: string;
  position?: 'bottom-right' | 'bottom-left';
}

const LiveChatWidget: React.FC<ChatWidgetProps> = ({
  customerId,
  customerName,
  customerEmail,
  position = 'bottom-right',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [session, setSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [agentTyping, setAgentTyping] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState<
    'disconnected' | 'connecting' | 'connected' | 'error'
  >('disconnected');

  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initialize chat session
  const initializeChat = async () => {
    try {
      // Create chat session via API
      const sessionData = {
        customer_name: customerName || 'Anonymous',
        customer_email: customerEmail,
        initial_message: '',
        page_url: window.location.href,
        user_agent: navigator.userAgent,
        metadata: {
          referrer: document.referrer,
          screen_resolution: `${screen.width}x${screen.height}`,
        },
      };

      // In production, this would be a real API call
      // const response = await fetch('/api/chat/sessions', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(sessionData)
      // });
      // const session = await response.json();

      // Mock session for demonstration
      const mockSession: ChatSession = {
        id: `session_${Date.now()}`,
        session_id: `chat_${Date.now()}`,
        status: 'waiting',
        created_at: new Date().toISOString(),
      };

      setSession(mockSession);
      connectWebSocket(mockSession.session_id);
    } catch (error) {
      console.error('Failed to initialize chat:', error);
      setConnectionStatus('error');
    }
  };

  // Connect to WebSocket
  const connectWebSocket = (sessionId: string) => {
    try {
      setConnectionStatus('connecting');

      // In production, this would connect to real WebSocket endpoint
      const wsUrl = `ws://localhost:8000/api/chat/ws/customer/${sessionId}`;
      // wsRef.current = new WebSocket(wsUrl);

      // Mock WebSocket connection for demonstration
      setTimeout(() => {
        setIsConnected(true);
        setConnectionStatus('connected');

        // Add welcome message
        const welcomeMessage: ChatMessage = {
          id: `msg_${Date.now()}`,
          type: 'system',
          content: 'Welcome to support chat! Please wait while we connect you to an agent.',
          sender_type: 'system',
          sender_name: 'System',
          timestamp: new Date().toISOString(),
        };

        setMessages([welcomeMessage]);

        // Simulate agent joining after a delay
        setTimeout(() => {
          const agentJoinMessage: ChatMessage = {
            id: `msg_${Date.now() + 1}`,
            type: 'agent_join',
            content: "Hi there! I'm Sarah from the support team. How can I help you today?",
            sender_type: 'agent',
            sender_name: 'Sarah',
            timestamp: new Date().toISOString(),
          };

          setMessages((prev) => [...prev, agentJoinMessage]);
          setSession((prev) =>
            prev ? { ...prev, status: 'active', assigned_agent_name: 'Sarah' } : null
          );
        }, 3000);
      }, 1000);

      /* Real WebSocket implementation:
      wsRef.current.onopen = () => {
        setIsConnected(true);
        setConnectionStatus('connected');
      };

      wsRef.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      };

      wsRef.current.onclose = () => {
        setIsConnected(false);
        setConnectionStatus('disconnected');
      };

      wsRef.current.onerror = () => {
        setConnectionStatus('error');
      };
      */
    } catch (error) {
      console.error('WebSocket connection error:', error);
      setConnectionStatus('error');
    }
  };

  // Handle WebSocket messages
  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'message':
        const message: ChatMessage = {
          id: data.id || `msg_${Date.now()}`,
          type: 'message',
          content: data.content,
          sender_type: data.sender_type,
          sender_name: data.sender_name,
          timestamp: data.timestamp,
          delivered: true,
        };
        setMessages((prev) => [...prev, message]);

        if (!isOpen) {
          setUnreadCount((prev) => prev + 1);
        }
        break;

      case 'typing':
        if (data.sender_type === 'agent') {
          setAgentTyping(true);
          setTimeout(() => setAgentTyping(false), 3000);
        }
        break;

      case 'agent_joined':
        setSession((prev) =>
          prev
            ? {
                ...prev,
                status: 'active',
                assigned_agent_name: data.agent_name,
              }
            : null
        );
        break;

      case 'agent_disconnected':
        const disconnectMessage: ChatMessage = {
          id: `msg_${Date.now()}`,
          type: 'system',
          content:
            data.message ||
            'Agent disconnected. Please wait while we connect you to another agent.',
          sender_type: 'system',
          sender_name: 'System',
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, disconnectMessage]);
        break;
    }
  };

  // Send message
  const sendMessage = () => {
    if (!newMessage.trim() || !isConnected || !session) return;

    const message: ChatMessage = {
      id: `msg_${Date.now()}`,
      type: 'message',
      content: newMessage.trim(),
      sender_type: 'customer',
      sender_name: customerName || 'You',
      timestamp: new Date().toISOString(),
      delivered: false,
    };

    setMessages((prev) => [...prev, message]);

    // Mock sending to WebSocket
    // wsRef.current?.send(JSON.stringify({
    //   type: 'message',
    //   content: newMessage.trim(),
    //   sender_name: customerName || 'Customer'
    // }));

    // Mock agent response after delay
    setTimeout(() => {
      const agentResponse: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        type: 'message',
        content:
          "Thank you for your message. Let me help you with that. Can you provide more details about the issue you're experiencing?",
        sender_type: 'agent',
        sender_name: 'Sarah',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, agentResponse]);
    }, 2000);

    setNewMessage('');
    setIsTyping(false);
  };

  // Handle typing indicator
  const handleTyping = (value: string) => {
    setNewMessage(value);

    if (!isTyping && value.trim()) {
      setIsTyping(true);
      // Send typing indicator to agent
      // wsRef.current?.send(JSON.stringify({ type: 'typing' }));
    }

    // Clear typing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Set new timeout
    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
    }, 1000);
  };

  // Handle key press
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // Open chat widget
  const openChat = () => {
    setIsOpen(true);
    setUnreadCount(0);

    if (!session) {
      initializeChat();
    }
  };

  // Close chat widget
  const closeChat = () => {
    setIsOpen(false);
    setIsMinimized(false);
  };

  // Toggle minimize
  const toggleMinimize = () => {
    setIsMinimized(!isMinimized);
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
        return 'bg-yellow-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = () => {
    switch (connectionStatus) {
      case 'connected':
        return session?.status === 'active' ? 'Connected to agent' : 'Waiting for agent';
      case 'connecting':
        return 'Connecting...';
      case 'error':
        return 'Connection error';
      default:
        return 'Disconnected';
    }
  };

  const MessageBubble: React.FC<{ message: ChatMessage }> = ({ message }) => {
    const isCustomer = message.sender_type === 'customer';
    const isSystem = message.sender_type === 'system';

    if (isSystem) {
      return (
        <div className='flex justify-center my-4'>
          <div className='bg-gray-100 px-3 py-2 rounded-lg text-sm text-gray-600 max-w-xs text-center'>
            {message.content}
          </div>
        </div>
      );
    }

    return (
      <div className={`flex ${isCustomer ? 'justify-end' : 'justify-start'} mb-4`}>
        <div
          className={`flex items-end space-x-2 max-w-xs lg:max-w-md ${isCustomer ? 'flex-row-reverse space-x-reverse' : ''}`}
        >
          {!isCustomer && (
            <Avatar className='h-6 w-6'>
              <AvatarFallback className='text-xs bg-blue-500 text-white'>
                {message.sender_name?.[0] || 'A'}
              </AvatarFallback>
            </Avatar>
          )}

          <div
            className={`px-3 py-2 rounded-lg ${
              isCustomer ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-900'
            }`}
          >
            <p className='text-sm'>{message.content}</p>
            <div
              className={`flex items-center justify-between mt-1 text-xs ${
                isCustomer ? 'text-blue-100' : 'text-gray-500'
              }`}
            >
              <span>{formatTime(message.timestamp)}</span>
              {isCustomer && message.delivered && <CheckCircle2 className='h-3 w-3' />}
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <>
      {/* Chat Button */}
      {!isOpen && (
        <Button
          id='live-chat-widget'
          onClick={openChat}
          className={`fixed ${position === 'bottom-right' ? 'bottom-6 right-6' : 'bottom-6 left-6'} 
            h-14 w-14 rounded-full shadow-lg z-50 bg-blue-600 hover:bg-blue-700`}
        >
          <MessageCircle className='h-6 w-6' />
          {unreadCount > 0 && (
            <Badge className='absolute -top-1 -right-1 h-5 w-5 p-0 bg-red-500 text-xs flex items-center justify-center'>
              {unreadCount > 9 ? '9+' : unreadCount}
            </Badge>
          )}
        </Button>
      )}

      {/* Chat Widget */}
      {isOpen && (
        <Card
          className={`fixed ${position === 'bottom-right' ? 'bottom-6 right-6' : 'bottom-6 left-6'} 
          w-80 h-96 shadow-2xl z-50 flex flex-col ${isMinimized ? 'h-14' : 'h-96'}`}
        >
          {/* Header */}
          <CardHeader className='p-4 bg-blue-600 text-white rounded-t-lg flex flex-row items-center justify-between space-y-0'>
            <div className='flex items-center space-x-2'>
              <div className={`h-2 w-2 rounded-full ${getStatusColor()}`} />
              <div>
                <CardTitle className='text-sm font-medium'>
                  {session?.assigned_agent_name
                    ? `Chat with ${session.assigned_agent_name}`
                    : 'Live Support'}
                </CardTitle>
                <p className='text-xs text-blue-100'>{getStatusText()}</p>
              </div>
            </div>
            <div className='flex items-center space-x-1'>
              <Button
                variant='ghost'
                size='sm'
                onClick={toggleMinimize}
                className='h-6 w-6 p-0 text-white hover:bg-blue-700'
              >
                {isMinimized ? (
                  <Maximize2 className='h-3 w-3' />
                ) : (
                  <Minimize2 className='h-3 w-3' />
                )}
              </Button>
              <Button
                variant='ghost'
                size='sm'
                onClick={closeChat}
                className='h-6 w-6 p-0 text-white hover:bg-blue-700'
              >
                <X className='h-3 w-3' />
              </Button>
            </div>
          </CardHeader>

          {!isMinimized && (
            <>
              {/* Messages */}
              <ScrollArea className='flex-1 p-4'>
                <div className='space-y-1'>
                  {messages.map((message) => (
                    <MessageBubble key={message.id} message={message} />
                  ))}

                  {/* Typing Indicator */}
                  {agentTyping && (
                    <div className='flex justify-start mb-4'>
                      <div className='flex items-center space-x-2'>
                        <Avatar className='h-6 w-6'>
                          <AvatarFallback className='text-xs bg-blue-500 text-white'>
                            {session?.assigned_agent_name?.[0] || 'A'}
                          </AvatarFallback>
                        </Avatar>
                        <div className='bg-gray-100 px-3 py-2 rounded-lg'>
                          <div className='flex space-x-1'>
                            <div className='w-2 h-2 bg-gray-400 rounded-full animate-bounce' />
                            <div
                              className='w-2 h-2 bg-gray-400 rounded-full animate-bounce'
                              style={{ animationDelay: '0.1s' }}
                            />
                            <div
                              className='w-2 h-2 bg-gray-400 rounded-full animate-bounce'
                              style={{ animationDelay: '0.2s' }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              </ScrollArea>

              {/* Message Input */}
              <div className='p-4 border-t'>
                {connectionStatus === 'error' && (
                  <div className='mb-2 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-600'>
                    Connection error. Please refresh the page and try again.
                  </div>
                )}

                {session?.status === 'waiting' && (
                  <div className='mb-2 p-2 bg-blue-50 border border-blue-200 rounded text-sm text-blue-600 flex items-center'>
                    <Clock className='h-4 w-4 mr-2' />
                    Waiting for an agent to join...
                  </div>
                )}

                <div className='flex items-end space-x-2'>
                  <div className='flex-1'>
                    <Textarea
                      ref={inputRef}
                      value={newMessage}
                      onChange={(e) => handleTyping(e.target.value)}
                      onKeyPress={handleKeyPress}
                      placeholder='Type your message...'
                      className='min-h-[40px] max-h-24 resize-none'
                      disabled={!isConnected || session?.status === 'ended'}
                      rows={1}
                    />
                  </div>
                  <Button
                    onClick={sendMessage}
                    disabled={!newMessage.trim() || !isConnected || session?.status === 'ended'}
                    size='sm'
                    className='h-10 w-10 p-0'
                  >
                    <Send className='h-4 w-4' />
                  </Button>
                </div>
              </div>
            </>
          )}
        </Card>
      )}
    </>
  );
};

export default LiveChatWidget;
