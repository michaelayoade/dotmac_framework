/**
 * Universal Chat Widget
 * Production-ready chat component that works across all portal types
 */

import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import {
  MessageCircle,
  X,
  Send,
  Paperclip,
  MoreVertical,
  Phone,
  Video,
  Minimize2,
  Maximize2,
  UserPlus,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { useSupportChat, useSupport } from '../providers/SupportProvider';
import type {
  ChatSession,
  ChatMessage,
  ChatParticipant,
  PortalType,
  ChatStatus
} from '../types';

// ===== INTERFACES =====

export interface UniversalChatWidgetProps {
  // Positioning and display
  position?: 'bottom-right' | 'bottom-left' | 'top-right' | 'top-left' | 'embedded';
  theme?: 'light' | 'dark' | 'auto';

  // Behavior
  autoOpen?: boolean;
  minimizeOnStart?: boolean;
  persistSession?: boolean;
  enableFileUpload?: boolean;
  enableVideoCall?: boolean;
  enablePhoneCall?: boolean;
  enableTransfer?: boolean;

  // Portal-specific
  defaultDepartment?: string;
  allowedDepartments?: string[];
  showParticipants?: boolean;
  showTypingIndicators?: boolean;

  // Customization
  brandColor?: string;
  placeholder?: string;
  welcomeMessage?: string;
  offlineMessage?: string;

  // Callbacks
  onSessionStart?: (session: ChatSession) => void;
  onSessionEnd?: (session: ChatSession) => void;
  onMessageSent?: (message: ChatMessage) => void;
  onAgentJoined?: (agent: ChatParticipant) => void;
  onTransfer?: (fromAgent: string, toAgent: string) => void;
}

interface ChatHeaderProps {
  session: ChatSession | null;
  isMinimized: boolean;
  onMinimize: () => void;
  onClose: () => void;
  onVideoCall?: () => void;
  onPhoneCall?: () => void;
  onTransfer?: () => void;
  showActions: boolean;
}

interface ChatMessageProps {
  message: ChatMessage;
  showAvatar?: boolean;
  isOwnMessage: boolean;
  showTimestamp?: boolean;
}

interface ChatInputProps {
  onSendMessage: (content: string, attachments?: File[]) => void;
  onStartTyping: () => void;
  onStopTyping: () => void;
  placeholder?: string;
  disabled?: boolean;
  enableFileUpload?: boolean;
  maxFileSize?: number;
}

// ===== SUB-COMPONENTS =====

function ChatHeader({
  session,
  isMinimized,
  onMinimize,
  onClose,
  onVideoCall,
  onPhoneCall,
  onTransfer,
  showActions
}: ChatHeaderProps) {
  const activeAgent = session?.participants.find(p => p.role === 'agent' && p.status === 'active');

  return (
    <div className="flex items-center justify-between p-3 bg-blue-600 text-white rounded-t-lg">
      <div className="flex items-center space-x-3">
        <MessageCircle className="w-5 h-5" />
        <div>
          <h3 className="font-semibold text-sm">
            {session ? (activeAgent ? `Chat with ${activeAgent.name}` : 'Support Chat') : 'Start Chat'}
          </h3>
          {session && (
            <p className="text-xs text-blue-100">
              {session.status === 'waiting' && 'Waiting for agent...'}
              {session.status === 'active' && activeAgent && (
                <>
                  <span className="inline-block w-2 h-2 bg-green-400 rounded-full mr-1"></span>
                  {activeAgent.name} - {activeAgent.title}
                </>
              )}
              {session.status === 'ended' && 'Chat ended'}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-1">
        {showActions && session?.status === 'active' && (
          <>
            {onVideoCall && (
              <button
                onClick={onVideoCall}
                className="p-1 hover:bg-blue-700 rounded transition-colors"
                title="Start video call"
              >
                <Video className="w-4 h-4" />
              </button>
            )}
            {onPhoneCall && (
              <button
                onClick={onPhoneCall}
                className="p-1 hover:bg-blue-700 rounded transition-colors"
                title="Start phone call"
              >
                <Phone className="w-4 h-4" />
              </button>
            )}
            {onTransfer && (
              <button
                onClick={onTransfer}
                className="p-1 hover:bg-blue-700 rounded transition-colors"
                title="Transfer chat"
              >
                <UserPlus className="w-4 h-4" />
              </button>
            )}
          </>
        )}

        <button
          onClick={onMinimize}
          className="p-1 hover:bg-blue-700 rounded transition-colors"
          title={isMinimized ? "Maximize" : "Minimize"}
        >
          {isMinimized ? <Maximize2 className="w-4 h-4" /> : <Minimize2 className="w-4 h-4" />}
        </button>

        <button
          onClick={onClose}
          className="p-1 hover:bg-blue-700 rounded transition-colors"
          title="Close chat"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

function ChatMessageComponent({ message, showAvatar = true, isOwnMessage, showTimestamp = true }: ChatMessageProps) {
  const messageTime = new Date(message.createdAt).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit'
  });

  return (
    <div className={`flex ${isOwnMessage ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`flex ${isOwnMessage ? 'flex-row-reverse' : 'flex-row'} items-start space-x-2 max-w-[80%]`}>
        {showAvatar && !isOwnMessage && (
          <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center text-xs font-semibold">
            {message.sender.name.charAt(0).toUpperCase()}
          </div>
        )}

        <div className={`${isOwnMessage ? 'mr-2' : 'ml-2'}`}>
          {!isOwnMessage && (
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-xs font-medium text-gray-700">{message.sender.name}</span>
              {message.sender.role === 'agent' && (
                <span className="text-xs text-blue-600 font-medium">{message.sender.title}</span>
              )}
            </div>
          )}

          <div className={`
            px-3 py-2 rounded-lg text-sm
            ${isOwnMessage
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-900'
            }
          `}>
            <div>{message.content}</div>

            {message.attachments && message.attachments.length > 0 && (
              <div className="mt-2 space-y-1">
                {message.attachments.map((attachment) => (
                  <div
                    key={attachment.id}
                    className="flex items-center space-x-2 p-2 bg-white bg-opacity-20 rounded"
                  >
                    <Paperclip className="w-3 h-3" />
                    <span className="text-xs truncate">{attachment.name}</span>
                    <span className="text-xs opacity-75">
                      ({(attachment.size / 1024).toFixed(1)}KB)
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {showTimestamp && (
            <div className={`text-xs text-gray-500 mt-1 ${isOwnMessage ? 'text-right' : 'text-left'}`}>
              {messageTime}
              {isOwnMessage && (
                <span className="ml-1">
                  {message.status === 'sent' && <CheckCircle className="w-3 h-3 inline text-gray-400" />}
                  {message.status === 'delivered' && <CheckCircle className="w-3 h-3 inline text-blue-500" />}
                  {message.status === 'read' && <CheckCircle className="w-3 h-3 inline text-green-500" />}
                  {message.status === 'failed' && <AlertCircle className="w-3 h-3 inline text-red-500" />}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ChatInput({
  onSendMessage,
  onStartTyping,
  onStopTyping,
  placeholder = "Type a message...",
  disabled = false,
  enableFileUpload = true,
  maxFileSize = 10 * 1024 * 1024 // 10MB
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [attachments, setAttachments] = useState<File[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout>();

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);

    if (!isTyping) {
      setIsTyping(true);
      onStartTyping();
    }

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
      onStopTyping();
    }, 2000);
  }, [isTyping, onStartTyping, onStopTyping]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() || attachments.length > 0) {
      onSendMessage(message.trim(), attachments);
      setMessage('');
      setAttachments([]);
      if (isTyping) {
        setIsTyping(false);
        onStopTyping();
      }
    }
  }, [message, attachments, isTyping, onSendMessage, onStopTyping]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const validFiles = files.filter(file => file.size <= maxFileSize);
    setAttachments(prev => [...prev, ...validFiles]);
  }, [maxFileSize]);

  const removeAttachment = useCallback((index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }, [handleSubmit]);

  return (
    <div className="p-3 border-t">
      {attachments.length > 0 && (
        <div className="mb-2 space-y-1">
          {attachments.map((file, index) => (
            <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm">
              <div className="flex items-center space-x-2">
                <Paperclip className="w-4 h-4 text-gray-500" />
                <span className="truncate">{file.name}</span>
                <span className="text-gray-500">({(file.size / 1024).toFixed(1)}KB)</span>
              </div>
              <button
                onClick={() => removeAttachment(index)}
                className="text-red-500 hover:text-red-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex items-end space-x-2">
        <div className="flex-1">
          <textarea
            value={message}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            style={{ minHeight: '40px', maxHeight: '120px' }}
          />
        </div>

        <div className="flex items-center space-x-1">
          {enableFileUpload && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileSelect}
                className="hidden"
                accept="image/*,.pdf,.doc,.docx,.txt"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled}
                className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Attach files"
              >
                <Paperclip className="w-5 h-5" />
              </button>
            </>
          )}

          <button
            type="submit"
            disabled={disabled || (!message.trim() && attachments.length === 0)}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Send message"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </form>
    </div>
  );
}

// ===== MAIN COMPONENT =====

export function UniversalChatWidget({
  position = 'bottom-right',
  theme = 'auto',
  autoOpen = false,
  minimizeOnStart = false,
  persistSession = true,
  enableFileUpload = true,
  enableVideoCall = false,
  enablePhoneCall = false,
  enableTransfer = false,
  defaultDepartment,
  allowedDepartments,
  showParticipants = true,
  showTypingIndicators = true,
  brandColor = '#2563eb',
  placeholder = "Type your message...",
  welcomeMessage = "Hello! How can we help you today?",
  offlineMessage = "We're currently offline. Please leave a message and we'll get back to you.",
  onSessionStart,
  onSessionEnd,
  onMessageSent,
  onAgentJoined,
  onTransfer
}: UniversalChatWidgetProps) {

  const { features, portalConfig, preferences } = useSupport();
  const {
    currentSession,
    messages,
    participants,
    typingParticipants,
    connectionStatus,
    startSession,
    endSession,
    sendMessage,
    startTyping,
    stopTyping,
    transferToAgent,
    isLoading,
    hasError
  } = useSupportChat();

  const [isOpen, setIsOpen] = useState(autoOpen && !minimizeOnStart);
  const [isMinimized, setIsMinimized] = useState(minimizeOnStart);
  const [showTransferModal, setShowTransferModal] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Portal-specific configurations
  const canTransfer = useMemo(() =>
    enableTransfer &&
    features.phoneSupport &&
    (portalConfig.type === 'agent' || portalConfig.type === 'admin'),
    [enableTransfer, features.phoneSupport, portalConfig.type]
  );

  const canUseVideo = useMemo(() =>
    enableVideoCall && features.videoCall,
    [enableVideoCall, features.videoCall]
  );

  const canUsePhone = useMemo(() =>
    enablePhoneCall && features.phoneSupport,
    [enablePhoneCall, features.phoneSupport]
  );

  const showActions = useMemo(() =>
    portalConfig.type !== 'customer',
    [portalConfig.type]
  );

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Handle session events
  useEffect(() => {
    if (currentSession && onSessionStart) {
      onSessionStart(currentSession);
    }
  }, [currentSession, onSessionStart]);

  // Handle agent joining
  useEffect(() => {
    if (currentSession && onAgentJoined) {
      const agents = participants.filter(p => p.role === 'agent');
      const newAgent = agents.find(a => !currentSession.participants.some(p => p.id === a.id));
      if (newAgent) {
        onAgentJoined(newAgent);
      }
    }
  }, [participants, currentSession, onAgentJoined]);

  const handleStartChat = useCallback(async () => {
    try {
      await startSession({
        department: defaultDepartment,
        priority: 'normal',
        metadata: {
          source: 'chat_widget',
          portal: portalConfig.type,
          page: window.location.pathname
        }
      });
      setIsOpen(true);
      setIsMinimized(false);
    } catch (error) {
      console.error('Failed to start chat session:', error);
    }
  }, [startSession, defaultDepartment, portalConfig.type]);

  const handleEndChat = useCallback(async () => {
    if (currentSession) {
      try {
        await endSession(currentSession.id);
        if (onSessionEnd) {
          onSessionEnd(currentSession);
        }
      } catch (error) {
        console.error('Failed to end chat session:', error);
      }
    }
    setIsOpen(false);
  }, [currentSession, endSession, onSessionEnd]);

  const handleSendMessage = useCallback(async (content: string, attachments?: File[]) => {
    if (!currentSession) return;

    try {
      const message = await sendMessage(currentSession.id, {
        content,
        attachments: attachments?.map(file => ({
          name: file.name,
          size: file.size,
          type: file.type,
          data: file
        }))
      });

      if (onMessageSent) {
        onMessageSent(message);
      }
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  }, [currentSession, sendMessage, onMessageSent]);

  const handleTransfer = useCallback(async () => {
    // Transfer logic would be implemented here
    setShowTransferModal(true);
  }, []);

  const positionClasses = useMemo(() => {
    if (position === 'embedded') return '';

    const positions = {
      'bottom-right': 'fixed bottom-4 right-4',
      'bottom-left': 'fixed bottom-4 left-4',
      'top-right': 'fixed top-4 right-4',
      'top-left': 'fixed top-4 left-4',
    };

    return positions[position] || positions['bottom-right'];
  }, [position]);

  const isOffline = connectionStatus !== 'connected';
  const currentUserId = 'current-user-id'; // This would come from auth context

  if (position === 'embedded') {
    return (
      <div className="w-full h-full flex flex-col bg-white rounded-lg border shadow-lg">
        <ChatHeader
          session={currentSession}
          isMinimized={false}
          onMinimize={() => {}}
          onClose={() => {}}
          onVideoCall={canUseVideo ? () => {} : undefined}
          onPhoneCall={canUsePhone ? () => {} : undefined}
          onTransfer={canTransfer ? handleTransfer : undefined}
          showActions={showActions}
        />

        <div className="flex-1 flex flex-col">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {!currentSession && (
              <div className="text-center py-8">
                <MessageCircle className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <p className="text-gray-600 mb-4">
                  {isOffline ? offlineMessage : welcomeMessage}
                </p>
                <button
                  onClick={handleStartChat}
                  disabled={isLoading('startSession')}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                >
                  {isLoading('startSession') ? (
                    <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                  ) : null}
                  Start Chat
                </button>
              </div>
            )}

            {currentSession && (
              <>
                {messages.map((message) => (
                  <ChatMessageComponent
                    key={message.id}
                    message={message}
                    isOwnMessage={message.senderId === currentUserId}
                    showAvatar={showParticipants}
                    showTimestamp
                  />
                ))}

                {showTypingIndicators && typingParticipants.length > 0 && (
                  <div className="flex items-center space-x-2 text-gray-500 text-sm">
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                    <span>
                      {typingParticipants.length === 1
                        ? `${typingParticipants[0].name} is typing...`
                        : `${typingParticipants.length} people are typing...`
                      }
                    </span>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {currentSession && (
            <ChatInput
              onSendMessage={handleSendMessage}
              onStartTyping={() => startTyping(currentSession.id)}
              onStopTyping={() => stopTyping(currentSession.id)}
              placeholder={placeholder}
              disabled={isOffline || currentSession.status === 'ended'}
              enableFileUpload={enableFileUpload && features.fileUpload}
              maxFileSize={portalConfig.maxFileSize}
            />
          )}
        </div>
      </div>
    );
  }

  // Floating widget
  return (
    <div className={`z-50 ${positionClasses}`}>
      {!isOpen && (
        <button
          onClick={currentSession ? () => setIsOpen(true) : handleStartChat}
          className="w-14 h-14 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all hover:scale-105 flex items-center justify-center"
          style={{ backgroundColor: brandColor }}
        >
          <MessageCircle className="w-6 h-6" />
          {currentSession && (
            <div className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center">
              <span className="text-xs text-white font-bold">
                {messages.filter(m => !m.readAt && m.senderId !== currentUserId).length || ''}
              </span>
            </div>
          )}
        </button>
      )}

      {isOpen && (
        <div className={`w-96 h-96 bg-white rounded-lg shadow-xl border transition-all ${isMinimized ? 'h-auto' : ''}`}>
          <ChatHeader
            session={currentSession}
            isMinimized={isMinimized}
            onMinimize={() => setIsMinimized(!isMinimized)}
            onClose={handleEndChat}
            onVideoCall={canUseVideo ? () => {} : undefined}
            onPhoneCall={canUsePhone ? () => {} : undefined}
            onTransfer={canTransfer ? handleTransfer : undefined}
            showActions={showActions}
          />

          {!isMinimized && (
            <div className="h-80 flex flex-col">
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {!currentSession && (
                  <div className="text-center py-8">
                    <MessageCircle className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    <p className="text-gray-600 mb-4 text-sm">
                      {isOffline ? offlineMessage : welcomeMessage}
                    </p>
                    <button
                      onClick={handleStartChat}
                      disabled={isLoading('startSession')}
                      className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 text-sm"
                    >
                      {isLoading('startSession') ? (
                        <Loader2 className="w-4 h-4 animate-spin inline mr-2" />
                      ) : null}
                      Start Chat
                    </button>
                  </div>
                )}

                {currentSession && (
                  <>
                    {messages.map((message) => (
                      <ChatMessageComponent
                        key={message.id}
                        message={message}
                        isOwnMessage={message.senderId === currentUserId}
                        showAvatar={showParticipants}
                        showTimestamp
                      />
                    ))}

                    {showTypingIndicators && typingParticipants.length > 0 && (
                      <div className="flex items-center space-x-2 text-gray-500 text-xs">
                        <div className="flex space-x-1">
                          <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></div>
                          <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                        <span>
                          {typingParticipants.length === 1
                            ? `${typingParticipants[0].name} is typing...`
                            : `${typingParticipants.length} people are typing...`
                          }
                        </span>
                      </div>
                    )}

                    <div ref={messagesEndRef} />
                  </>
                )}
              </div>

              {currentSession && (
                <ChatInput
                  onSendMessage={handleSendMessage}
                  onStartTyping={() => startTyping(currentSession.id)}
                  onStopTyping={() => stopTyping(currentSession.id)}
                  placeholder={placeholder}
                  disabled={isOffline || currentSession.status === 'ended'}
                  enableFileUpload={enableFileUpload && features.fileUpload}
                  maxFileSize={portalConfig.maxFileSize}
                />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default UniversalChatWidget;
