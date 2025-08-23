'use client';

import { useState, useEffect, useRef } from 'react';
import { Card } from '@dotmac/styled-components/customer';
import {
  MessageSquare,
  X,
  Send,
  Paperclip,
  Smile,
  MinusCircle,
  Phone,
  Video,
  MoreHorizontal,
  User,
  Bot,
  CheckCheck,
  Clock,
  AlertCircle,
  Minimize2,
  Maximize2,
} from 'lucide-react';

interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'agent' | 'bot';
  timestamp: Date;
  status?: 'sending' | 'sent' | 'delivered' | 'read';
  type?: 'text' | 'image' | 'file' | 'system';
  agentName?: string;
  agentAvatar?: string;
}

interface ChatAgent {
  id: string;
  name: string;
  avatar?: string;
  status: 'online' | 'busy' | 'away';
  title: string;
  rating: number;
}

const mockMessages: ChatMessage[] = [
  {
    id: '1',
    content:
      "Hi! I'm here to help you with any questions about your DotMac services. How can I assist you today?",
    sender: 'bot',
    timestamp: new Date(Date.now() - 300000),
    status: 'delivered',
    type: 'text',
  },
];

const mockAgent: ChatAgent = {
  id: 'agent_1',
  name: 'Sarah Johnson',
  avatar: '/avatars/sarah.jpg',
  status: 'online',
  title: 'Technical Support Specialist',
  rating: 4.9,
};

const quickReplies = [
  'I need help with my internet',
  'Billing question',
  'Service outage',
  'Technical support',
  'Account settings',
];

export function LiveChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(mockMessages);
  const [newMessage, setNewMessage] = useState('');
  const [isAgentTyping, setIsAgentTyping] = useState(false);
  const [chatStatus, setChatStatus] = useState<'initializing' | 'connected' | 'waiting' | 'active'>(
    'connected'
  );
  const [unreadCount, setUnreadCount] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      setUnreadCount(0);
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const sendMessage = (content: string) => {
    if (!content.trim()) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      content: content.trim(),
      sender: 'user',
      timestamp: new Date(),
      status: 'sending',
      type: 'text',
    };

    setMessages((prev) => [...prev, userMessage]);
    setNewMessage('');

    // Simulate message delivery
    setTimeout(() => {
      setMessages((prev) =>
        prev.map((msg) => (msg.id === userMessage.id ? { ...msg, status: 'delivered' } : msg))
      );
    }, 1000);

    // Simulate agent typing and response
    setTimeout(() => {
      setIsAgentTyping(true);
    }, 1500);

    setTimeout(() => {
      setIsAgentTyping(false);
      const agentResponse: ChatMessage = {
        id: (Date.now() + 1).toString(),
        content: getAgentResponse(content),
        sender: 'agent',
        timestamp: new Date(),
        status: 'delivered',
        type: 'text',
        agentName: mockAgent.name,
        agentAvatar: mockAgent.avatar,
      };
      setMessages((prev) => [...prev, agentResponse]);

      if (!isOpen) {
        setUnreadCount((prev) => prev + 1);
      }
    }, 3000);
  };

  const getAgentResponse = (userMessage: string): string => {
    const lowerMessage = userMessage.toLowerCase();

    if (lowerMessage.includes('internet') || lowerMessage.includes('slow')) {
      return "I understand you're having internet issues. Let me help you troubleshoot. First, can you tell me if this is affecting all devices or just one specific device?";
    } else if (lowerMessage.includes('billing') || lowerMessage.includes('payment')) {
      return "I'd be happy to help with your billing question. For account security, I'll need to verify some information. Can you confirm the phone number on your account?";
    } else if (lowerMessage.includes('outage')) {
      return "I'm checking for any reported outages in your area. I can see your service address is 123 Main Street. I don't see any current outages, but let me run some diagnostics on your connection.";
    } else {
      return 'Thank you for that information. Let me look into this for you. Is there anything else I can help clarify while I research this?';
    }
  };

  const handleQuickReply = (reply: string) => {
    sendMessage(reply);
  };

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'sending':
        return <Clock className='h-3 w-3 text-gray-400' />;
      case 'sent':
      case 'delivered':
        return <CheckCheck className='h-3 w-3 text-gray-400' />;
      case 'read':
        return <CheckCheck className='h-3 w-3 text-blue-500' />;
      default:
        return null;
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className='fixed bottom-4 right-4 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-blue-600 text-white shadow-lg transition-all hover:bg-blue-700 hover:shadow-xl'
      >
        <MessageSquare className='h-6 w-6' />
        {unreadCount > 0 && (
          <span className='absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-xs font-bold text-white'>
            {unreadCount}
          </span>
        )}
      </button>
    );
  }

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 transition-all duration-300 ${
        isMinimized ? 'h-12' : 'h-96'
      } w-80 sm:w-96`}
    >
      <Card className='flex h-full flex-col overflow-hidden shadow-2xl'>
        {/* Chat Header */}
        <div className='flex items-center justify-between bg-blue-600 p-4 text-white'>
          <div className='flex items-center space-x-3'>
            <div className='relative'>
              <div className='h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center'>
                <User className='h-4 w-4' />
              </div>
              <div className='absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white bg-green-500'></div>
            </div>
            <div>
              <h3 className='font-medium text-sm'>{mockAgent.name}</h3>
              <p className='text-xs text-blue-100'>{mockAgent.title}</p>
            </div>
          </div>
          <div className='flex items-center space-x-2'>
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className='rounded p-1 hover:bg-blue-700 transition-colors'
            >
              {isMinimized ? <Maximize2 className='h-4 w-4' /> : <Minimize2 className='h-4 w-4' />}
            </button>
            <button
              onClick={() => setIsOpen(false)}
              className='rounded p-1 hover:bg-blue-700 transition-colors'
            >
              <X className='h-4 w-4' />
            </button>
          </div>
        </div>

        {!isMinimized && (
          <>
            {/* Chat Messages */}
            <div className='flex-1 overflow-y-auto p-4 space-y-4'>
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`flex max-w-xs lg:max-w-md items-end space-x-2 ${message.sender === 'user' ? 'flex-row-reverse space-x-reverse' : 'flex-row'}`}
                  >
                    {message.sender !== 'user' && (
                      <div className='h-6 w-6 rounded-full bg-gray-300 flex-shrink-0 flex items-center justify-center'>
                        {message.sender === 'bot' ? (
                          <Bot className='h-3 w-3 text-gray-600' />
                        ) : (
                          <User className='h-3 w-3 text-gray-600' />
                        )}
                      </div>
                    )}
                    <div>
                      <div
                        className={`rounded-lg px-4 py-2 ${
                          message.sender === 'user'
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-900'
                        }`}
                      >
                        <p className='text-sm'>{message.content}</p>
                      </div>
                      <div
                        className={`flex items-center mt-1 space-x-1 text-xs text-gray-500 ${
                          message.sender === 'user' ? 'justify-end' : 'justify-start'
                        }`}
                      >
                        <span>{formatTime(message.timestamp)}</span>
                        {message.sender === 'user' && getStatusIcon(message.status)}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Typing Indicator */}
              {isAgentTyping && (
                <div className='flex justify-start'>
                  <div className='flex items-end space-x-2'>
                    <div className='h-6 w-6 rounded-full bg-gray-300 flex-shrink-0 flex items-center justify-center'>
                      <User className='h-3 w-3 text-gray-600' />
                    </div>
                    <div className='bg-gray-100 rounded-lg px-4 py-2'>
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

            {/* Quick Replies */}
            {messages.length === 1 && (
              <div className='px-4 pb-2'>
                <div className='flex flex-wrap gap-2'>
                  {quickReplies.map((reply, index) => (
                    <button
                      key={index}
                      onClick={() => handleQuickReply(reply)}
                      className='rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-700 hover:bg-gray-200 transition-colors'
                    >
                      {reply}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Message Input */}
            <div className='border-t bg-white p-4'>
              <div className='flex items-center space-x-2'>
                <div className='flex-1 flex items-center space-x-2 rounded-full border border-gray-300 bg-white px-4 py-2'>
                  <input
                    ref={inputRef}
                    type='text'
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage(newMessage)}
                    placeholder='Type your message...'
                    className='flex-1 border-none outline-none text-sm'
                  />
                  <div className='flex items-center space-x-1'>
                    <button className='p-1 text-gray-400 hover:text-gray-600 transition-colors'>
                      <Paperclip className='h-4 w-4' />
                    </button>
                    <button className='p-1 text-gray-400 hover:text-gray-600 transition-colors'>
                      <Smile className='h-4 w-4' />
                    </button>
                  </div>
                </div>
                <button
                  onClick={() => sendMessage(newMessage)}
                  disabled={!newMessage.trim()}
                  className='rounded-full bg-blue-600 p-2 text-white hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed'
                >
                  <Send className='h-4 w-4' />
                </button>
              </div>

              {/* Action Buttons */}
              <div className='flex items-center justify-center mt-3 space-x-4'>
                <button className='flex items-center space-x-1 text-xs text-gray-600 hover:text-gray-800 transition-colors'>
                  <Phone className='h-3 w-3' />
                  <span>Call</span>
                </button>
                <button className='flex items-center space-x-1 text-xs text-gray-600 hover:text-gray-800 transition-colors'>
                  <Video className='h-3 w-3' />
                  <span>Video</span>
                </button>
                <button className='flex items-center space-x-1 text-xs text-gray-600 hover:text-gray-800 transition-colors'>
                  <MoreHorizontal className='h-3 w-3' />
                  <span>More</span>
                </button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
