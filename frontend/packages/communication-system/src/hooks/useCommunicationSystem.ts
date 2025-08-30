'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import type {
  CommunicationChannel,
  CommunicationMessage,
  CommunicationTemplate,
  CommunicationStats,
  BulkCommunicationJob,
  ChatConversation,
  ChatMessage,
  NotificationPreferences,
  CommunicationSystemConfig
} from '../types';

interface UseCommunicationSystemOptions {
  apiKey?: string;
  baseUrl?: string;
  websocketUrl?: string;
  enableRealtime?: boolean;
  enableCaching?: boolean;
  cacheTimeout?: number;
  tenantId?: string;
  userId?: string;
}

export function useCommunicationSystem(options: UseCommunicationSystemOptions = {}) {
  const [channels, setChannels] = useState<CommunicationChannel[]>([]);
  const [templates, setTemplates] = useState<CommunicationTemplate[]>([]);
  const [messages, setMessages] = useState<CommunicationMessage[]>([]);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [stats, setStats] = useState<CommunicationStats | null>(null);
  const [bulkJobs, setBulkJobs] = useState<BulkCommunicationJob[]>([]);
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const cacheRef = useRef<Map<string, any>>(new Map());

  const {
    apiKey,
    baseUrl = '/api/communication',
    websocketUrl,
    enableRealtime = true,
    enableCaching = true,
    cacheTimeout = 5 * 60 * 1000, // 5 minutes
    tenantId,
    userId
  } = options;

  // WebSocket connection management
  const connectWebSocket = useCallback(() => {
    if (!websocketUrl || !enableRealtime || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const ws = new WebSocket(websocketUrl);

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);

        // Authenticate and subscribe to relevant channels
        ws.send(JSON.stringify({
          type: 'authenticate',
          apiKey,
          tenantId,
          userId
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleRealtimeMessage(data);
        } catch (error) {
          console.warn('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        // Retry connection after 3 seconds
        retryTimeoutRef.current = setTimeout(connectWebSocket, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Real-time connection failed');
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setError('Failed to establish real-time connection');
    }
  }, [websocketUrl, enableRealtime, apiKey, tenantId, userId]);

  const handleRealtimeMessage = useCallback((data: any) => {
    switch (data.type) {
      case 'message_sent':
        setMessages(prev => [...prev, data.message]);
        break;

      case 'message_status_update':
        setMessages(prev => prev.map(msg =>
          msg.id === data.messageId
            ? { ...msg, status: data.status, deliveredAt: data.deliveredAt }
            : msg
        ));
        break;

      case 'new_chat_message':
        updateConversationWithMessage(data.conversationId, data.message);
        break;

      case 'conversation_update':
        setConversations(prev => prev.map(conv =>
          conv.id === data.conversationId
            ? { ...conv, ...data.updates }
            : conv
        ));
        break;

      case 'stats_update':
        setStats(data.stats);
        break;

      case 'bulk_job_progress':
        setBulkJobs(prev => prev.map(job =>
          job.id === data.jobId
            ? { ...job, progress: data.progress, status: data.status }
            : job
        ));
        break;
    }
  }, []);

  // API request wrapper with caching
  const apiRequest = useCallback(async (endpoint: string, options: RequestInit = {}) => {
    const cacheKey = `${endpoint}-${JSON.stringify(options)}`;

    // Check cache first
    if (enableCaching && options.method === 'GET') {
      const cached = cacheRef.current.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < cacheTimeout) {
        return cached.data;
      }
    }

    const headers = {
      'Content-Type': 'application/json',
      ...(apiKey && { 'Authorization': `Bearer ${apiKey}` }),
      ...(tenantId && { 'X-Tenant-ID': tenantId }),
      ...options.headers
    };

    const response = await fetch(`${baseUrl}${endpoint}`, {
      ...options,
      headers
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    const data = await response.json();

    // Cache successful GET requests
    if (enableCaching && options.method === 'GET') {
      cacheRef.current.set(cacheKey, {
        data,
        timestamp: Date.now()
      });
    }

    return data;
  }, [baseUrl, apiKey, tenantId, enableCaching, cacheTimeout]);

  // Core messaging functions
  const sendMessage = useCallback(async (messageData: Omit<CommunicationMessage, 'id' | 'status' | 'sentAt'>) => {
    setIsLoading(true);
    setError(null);

    try {
      const message = await apiRequest('/messages', {
        method: 'POST',
        body: JSON.stringify({
          ...messageData,
          tenantId,
          userId
        })
      });

      setMessages(prev => [...prev, message]);
      return message;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      setError(errorMessage);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [apiRequest, tenantId, userId]);

  const sendBulkMessages = useCallback(async (messagesData: Array<Omit<CommunicationMessage, 'id' | 'status' | 'sentAt'>>) => {
    setIsLoading(true);
    setError(null);

    try {
      const job = await apiRequest('/messages/bulk', {
        method: 'POST',
        body: JSON.stringify({
          messages: messagesData.map(msg => ({
            ...msg,
            tenantId,
            userId
          }))
        })
      });

      setBulkJobs(prev => [...prev, job]);
      return job;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send bulk messages';
      setError(errorMessage);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, [apiRequest, tenantId, userId]);

  // Template management
  const createTemplate = useCallback(async (templateData: Omit<CommunicationTemplate, 'id' | 'createdAt' | 'updatedAt'>) => {
    try {
      const template = await apiRequest('/templates', {
        method: 'POST',
        body: JSON.stringify(templateData)
      });

      setTemplates(prev => [...prev, template]);
      return template;
    } catch (error) {
      setError('Failed to create template');
      throw error;
    }
  }, [apiRequest]);

  const updateTemplate = useCallback(async (templateId: string, updates: Partial<CommunicationTemplate>) => {
    try {
      const template = await apiRequest(`/templates/${templateId}`, {
        method: 'PATCH',
        body: JSON.stringify(updates)
      });

      setTemplates(prev => prev.map(t => t.id === templateId ? template : t));
      return template;
    } catch (error) {
      setError('Failed to update template');
      throw error;
    }
  }, [apiRequest]);

  // Chat functions
  const sendChatMessage = useCallback(async (conversationId: string, content: string, type: 'text' | 'image' | 'file' = 'text') => {
    const messageData: Omit<ChatMessage, 'id' | 'timestamp' | 'status'> = {
      content,
      sender: 'user',
      senderId: userId,
      conversationId,
      type
    };

    try {
      const message = await apiRequest(`/chat/conversations/${conversationId}/messages`, {
        method: 'POST',
        body: JSON.stringify(messageData)
      });

      updateConversationWithMessage(conversationId, message);
      return message;
    } catch (error) {
      setError('Failed to send chat message');
      throw error;
    }
  }, [apiRequest, userId]);

  const createConversation = useCallback(async (participantIds: string[], title?: string) => {
    try {
      const conversation = await apiRequest('/chat/conversations', {
        method: 'POST',
        body: JSON.stringify({
          participantIds,
          title,
          tenantId
        })
      });

      setConversations(prev => [...prev, conversation]);
      return conversation;
    } catch (error) {
      setError('Failed to create conversation');
      throw error;
    }
  }, [apiRequest, tenantId]);

  // Helper functions
  const updateConversationWithMessage = useCallback((conversationId: string, message: ChatMessage) => {
    setConversations(prev => prev.map(conv => {
      if (conv.id === conversationId) {
        return {
          ...conv,
          lastMessage: message,
          updatedAt: new Date(),
          unreadCount: message.sender !== 'user' ? conv.unreadCount + 1 : conv.unreadCount
        };
      }
      return conv;
    }));
  }, []);

  const markConversationAsRead = useCallback(async (conversationId: string) => {
    try {
      await apiRequest(`/chat/conversations/${conversationId}/read`, {
        method: 'POST'
      });

      setConversations(prev => prev.map(conv =>
        conv.id === conversationId
          ? { ...conv, unreadCount: 0 }
          : conv
      ));
    } catch (error) {
      console.error('Failed to mark conversation as read:', error);
    }
  }, [apiRequest]);

  // Data fetching
  const loadChannels = useCallback(async () => {
    try {
      const channelsData = await apiRequest('/channels');
      setChannels(channelsData);
    } catch (error) {
      setError('Failed to load channels');
    }
  }, [apiRequest]);

  const loadTemplates = useCallback(async () => {
    try {
      const templatesData = await apiRequest('/templates');
      setTemplates(templatesData);
    } catch (error) {
      setError('Failed to load templates');
    }
  }, [apiRequest]);

  const loadMessages = useCallback(async (filters?: any) => {
    try {
      const query = filters ? `?${new URLSearchParams(filters)}` : '';
      const messagesData = await apiRequest(`/messages${query}`);
      setMessages(messagesData);
    } catch (error) {
      setError('Failed to load messages');
    }
  }, [apiRequest]);

  const loadConversations = useCallback(async () => {
    try {
      const conversationsData = await apiRequest('/chat/conversations');
      setConversations(conversationsData);
    } catch (error) {
      setError('Failed to load conversations');
    }
  }, [apiRequest]);

  const loadStats = useCallback(async () => {
    try {
      const statsData = await apiRequest('/stats');
      setStats(statsData);
    } catch (error) {
      setError('Failed to load stats');
    }
  }, [apiRequest]);

  // Initialize
  useEffect(() => {
    if (enableRealtime) {
      connectWebSocket();
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }
    };
  }, [connectWebSocket, enableRealtime]);

  // Auto-load initial data
  useEffect(() => {
    Promise.allSettled([
      loadChannels(),
      loadTemplates(),
      loadMessages(),
      loadConversations(),
      loadStats()
    ]);
  }, [loadChannels, loadTemplates, loadMessages, loadConversations, loadStats]);

  return {
    // State
    channels,
    templates,
    messages,
    conversations,
    stats,
    bulkJobs,
    preferences,
    isConnected,
    isLoading,
    error,

    // Actions
    sendMessage,
    sendBulkMessages,
    sendChatMessage,
    createConversation,
    createTemplate,
    updateTemplate,
    markConversationAsRead,

    // Data loading
    loadChannels,
    loadTemplates,
    loadMessages,
    loadConversations,
    loadStats,

    // Utilities
    clearError: () => setError(null),
    clearCache: () => cacheRef.current.clear(),
    disconnect: () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    }
  };
}
