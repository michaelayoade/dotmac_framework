'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  MessageSquare,
  X,
  Send,
  Paperclip,
  Smile,
  Minimize2,
  Maximize2,
  User,
  Bot,
  CheckCheck,
  Clock,
  AlertCircle,
  Phone,
  Video,
  MoreHorizontal
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ChatMessage, ChatConversation, ChatParticipant } from '../../types';
import { useCommunicationSystem } from '../../hooks/useCommunicationSystem';

interface LiveChatWidgetProps {
  conversationId?: string;
  userId?: string;
  tenantId?: string;
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left';
  theme?: 'light' | 'dark' | 'brand';
  enableFileUpload?: boolean;
  enableEmoji?: boolean;
  enableVideo?: boolean;
  enableVoice?: boolean;
  quickReplies?: string[];
  placeholder?: string;
  className?: string;
  onConversationStart?: (conversationId: string) => void;
  onConversationEnd?: (conversationId: string) => void;
  onMessageSent?: (message: ChatMessage) => void;
}

const defaultQuickReplies = [
  'I need help with my internet',
  'Billing question',
  'Service outage',
  'Technical support',
  'Account settings',
];

const positionClasses = {
  'bottom-right': 'bottom-4 right-4',
  'bottom-left': 'bottom-4 left-4',
  'top-right': 'top-4 right-4',
  'top-left': 'top-4 left-4'
};

export function LiveChatWidget({
  conversationId,
  userId,
  tenantId,
  position = 'bottom-right',
  theme = 'light',
  enableFileUpload = true,
  enableEmoji = true,
  enableVideo = false,
  enableVoice = false,
  quickReplies = defaultQuickReplies,
  placeholder = 'Type your message...',
  className = '',
  onConversationStart,
  onConversationEnd,
  onMessageSent
}: LiveChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [currentConversation, setCurrentConversation] = useState<ChatConversation | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const communication = useCommunicationSystem({
    tenantId,
    userId,
    enableRealtime: true
  });

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  const handleSendMessage = useCallback(async () => {
    if (!newMessage.trim() || !currentConversation) return;

    const messageContent = newMessage.trim();
    setNewMessage('');

    try {
      const message = await communication.sendChatMessage(
        currentConversation.id,
        messageContent,
        'text'
      );

      setMessages(prev => [...prev, message]);
      onMessageSent?.(message);
      scrollToBottom();
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  }, [newMessage, currentConversation, communication, onMessageSent, scrollToBottom]);

  const handleQuickReply = useCallback((reply: string) => {
    setNewMessage(reply);
    setTimeout(() => handleSendMessage(), 100);
  }, [handleSendMessage]);

  const handleTyping = useCallback(() => {
    setIsTyping(true);

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
    }, 1000);
  }, []);

  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !currentConversation) return;

    // TODO: Implement file upload logic
    console.log('File upload:', file);
  }, [currentConversation]);

  const startConversation = useCallback(async () => {
    if (!userId) return;

    try {
      const conversation = await communication.createConversation([userId], 'Customer Support');
      setCurrentConversation(conversation);
      onConversationStart?.(conversation.id);

      // Load messages for this conversation
      // TODO: Implement message loading
      setMessages([]);
    } catch (error) {
      console.error('Failed to start conversation:', error);
    }
  }, [userId, communication, onConversationStart]);

  const closeChat = useCallback(() => {
    setIsOpen(false);
    setUnreadCount(0);

    if (currentConversation) {
      onConversationEnd?.(currentConversation.id);
    }
  }, [currentConversation, onConversationEnd]);

  const openChat = useCallback(() => {
    setIsOpen(true);
    setUnreadCount(0);

    if (!currentConversation) {
      startConversation();
    }

    setTimeout(() => {
      inputRef.current?.focus();
    }, 100);
  }, [currentConversation, startConversation]);

  const getMessageStatus = useCallback((message: ChatMessage) => {
    switch (message.status) {
      case 'sending':
        return <Clock className="w-3 h-3 text-gray-400" />;
      case 'sent':
        return <CheckCheck className="w-3 h-3 text-gray-400" />;
      case 'delivered':
        return <CheckCheck className="w-3 h-3 text-blue-500" />;
      case 'read':
        return <CheckCheck className="w-3 h-3 text-blue-500" />;
      case 'failed':
        return <AlertCircle className="w-3 h-3 text-red-500" />;
      default:
        return null;
    }
  }, []);

  const formatTime = useCallback((date: Date) => {
    return new Intl.DateTimeFormat('en', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    }).format(date);
  }, []);

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, scrollToBottom]);

  useEffect(() => {
    if (!isOpen && messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.sender !== 'user') {
        setUnreadCount(prev => prev + 1);
      }
    }
  }, [messages, isOpen]);

  const themeClasses = {
    light: 'bg-white text-gray-900 border-gray-200',
    dark: 'bg-gray-900 text-white border-gray-700',
    brand: 'bg-blue-600 text-white border-blue-500'
  };

  if (!isOpen) {
    return (
      <div className={`fixed z-50 ${positionClasses[position]} ${className}`}>
        <motion.button
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={openChat}
          className="w-14 h-14 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg flex items-center justify-center transition-colors relative"
        >
          <MessageSquare className="w-6 h-6" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </motion.button>
      </div>
    );
  }

  return (
    <div className={`fixed z-50 ${positionClasses[position]} ${className}`}>
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{
          opacity: 1,
          y: 0,
          scale: 1,
          height: isMinimized ? 'auto' : '500px'
        }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        className={`w-80 rounded-lg shadow-xl border ${themeClasses[theme]} overflow-hidden`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-medium text-sm">Customer Support</h3>
              <p className="text-xs opacity-70">
                {communication.isConnected ? 'Online' : 'Connecting...'}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-1">
            {enableVoice && (
              <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                <Phone className="w-4 h-4" />
              </button>
            )}
            {enableVideo && (
              <button className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
                <Video className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            >
              {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
            </button>
            <button
              onClick={closeChat}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <AnimatePresence>
          {!isMinimized && (
            <motion.div
              initial={{ height: 0 }}
              animate={{ height: 'auto' }}
              exit={{ height: 0 }}
              className="flex flex-col"
            >
              {/* Messages */}
              <div className="flex-1 p-4 space-y-3 h-80 overflow-y-auto">
                {messages.length === 0 ? (
                  <div className="text-center py-8">
                    <Bot className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p className="text-sm text-gray-500">
                      Hi! How can we help you today?
                    </p>
                  </div>
                ) : (
                  <>
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div className={`max-w-[80%] ${message.sender === 'user' ? 'order-2' : 'order-1'}`}>
                          {message.sender !== 'user' && (
                            <div className="flex items-center space-x-2 mb-1">
                              <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
                                {message.sender === 'bot' ? (
                                  <Bot className="w-3 h-3 text-blue-600" />
                                ) : (
                                  <User className="w-3 h-3 text-blue-600" />
                                )}
                              </div>
                              <span className="text-xs text-gray-500">
                                {message.senderName || 'Support Agent'}
                              </span>
                            </div>
                          )}

                          <div
                            className={`px-3 py-2 rounded-lg text-sm ${
                              message.sender === 'user'
                                ? 'bg-blue-600 text-white ml-2'
                                : 'bg-gray-100 dark:bg-gray-800 mr-2'
                            }`}
                          >
                            {message.content}
                          </div>

                          <div className={`flex items-center space-x-1 mt-1 text-xs text-gray-500 ${
                            message.sender === 'user' ? 'justify-end' : 'justify-start'
                          }`}>
                            <span>{formatTime(message.timestamp)}</span>
                            {message.sender === 'user' && getMessageStatus(message)}
                          </div>
                        </div>
                      </div>
                    ))}

                    {isTyping && (
                      <div className="flex justify-start">
                        <div className="bg-gray-100 dark:bg-gray-800 px-3 py-2 rounded-lg">
                          <div className="flex space-x-1">
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse"></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{animationDelay: '0.1s'}}></div>
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                          </div>
                        </div>
                      </div>
                    )}

                    <div ref={messagesEndRef} />
                  </>
                )}
              </div>

              {/* Quick Replies */}
              {messages.length === 0 && quickReplies.length > 0 && (
                <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700">
                  <p className="text-xs text-gray-500 mb-2">Quick replies:</p>
                  <div className="space-y-1">
                    {quickReplies.slice(0, 3).map((reply, index) => (
                      <button
                        key={index}
                        onClick={() => handleQuickReply(reply)}
                        className="w-full text-left text-xs p-2 rounded bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                      >
                        {reply}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Input */}
              <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center space-x-2">
                  <div className="flex-1 relative">
                    <input
                      ref={inputRef}
                      type="text"
                      value={newMessage}
                      onChange={(e) => {
                        setNewMessage(e.target.value);
                        handleTyping();
                      }}
                      onKeyPress={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                      placeholder={placeholder}
                      className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-transparent text-sm"
                    />
                  </div>

                  <div className="flex items-center space-x-1">
                    {enableFileUpload && (
                      <>
                        <button
                          onClick={() => fileInputRef.current?.click()}
                          className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
                        >
                          <Paperclip className="w-4 h-4" />
                        </button>
                        <input
                          ref={fileInputRef}
                          type="file"
                          onChange={handleFileUpload}
                          className="hidden"
                          accept="image/*,.pdf,.doc,.docx"
                        />
                      </>
                    )}

                    {enableEmoji && (
                      <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors">
                        <Smile className="w-4 h-4" />
                      </button>
                    )}

                    <button
                      onClick={handleSendMessage}
                      disabled={!newMessage.trim()}
                      className="p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
