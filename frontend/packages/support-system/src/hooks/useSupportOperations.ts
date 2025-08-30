/**
 * Universal Support Operations Hook
 * Production-ready hook for all support and communication operations
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type {
  SupportTicket,
  ChatSession,
  ChatMessage,
  KnowledgeBaseArticle,
  UploadedFile,
  SearchResult,
  SearchFilters,
  ApiResponse,
  PaginatedResponse,
  SupportConfig,
  PortalType,
  TicketStatus,
  ChatStatus,
  FileUploadConfig,
  SupportMetrics
} from '../types';

// ===== CONFIGURATION =====

export interface SupportOperationsConfig {
  portalType: PortalType;
  baseUrl: string;
  apiVersion?: string;
  timeout?: number;
  retryAttempts?: number;
  enableRealtime?: boolean;
  enableCaching?: boolean;
  cacheTimeout?: number;
  enableOffline?: boolean;
  features: {
    ticketing: boolean;
    liveChat: boolean;
    knowledgeBase: boolean;
    fileUpload: boolean;
    analytics: boolean;
  };
}

export interface UseSupportOperationsReturn {
  // Configuration
  config: SupportOperationsConfig;
  isInitialized: boolean;

  // Support Tickets
  tickets: {
    list: (filters?: SearchFilters) => Promise<ApiResponse<PaginatedResponse<SupportTicket>>>;
    get: (ticketId: string) => Promise<ApiResponse<SupportTicket>>;
    create: (ticketData: Partial<SupportTicket>) => Promise<ApiResponse<SupportTicket>>;
    update: (ticketId: string, updates: Partial<SupportTicket>) => Promise<ApiResponse<SupportTicket>>;
    addMessage: (ticketId: string, message: string, attachments?: File[]) => Promise<ApiResponse<void>>;
    changeStatus: (ticketId: string, status: TicketStatus, reason?: string) => Promise<ApiResponse<void>>;
    assign: (ticketId: string, agentId: string) => Promise<ApiResponse<void>>;
    close: (ticketId: string, resolution?: string) => Promise<ApiResponse<void>>;
    search: (query: string, filters?: SearchFilters) => Promise<ApiResponse<SearchResult<SupportTicket>>>;
  };

  // Live Chat
  chat: {
    startSession: (customerId?: string) => Promise<ApiResponse<ChatSession>>;
    endSession: (sessionId: string) => Promise<ApiResponse<void>>;
    sendMessage: (sessionId: string, message: string, attachments?: File[]) => Promise<ApiResponse<ChatMessage>>;
    getMessages: (sessionId: string, limit?: number, before?: string) => Promise<ApiResponse<ChatMessage[]>>;
    transferToAgent: (sessionId: string, agentId: string, reason?: string) => Promise<ApiResponse<void>>;
    setTyping: (sessionId: string, isTyping: boolean) => void;
    getActiveSession: () => ChatSession | null;
    getSessionHistory: (customerId: string) => Promise<ApiResponse<ChatSession[]>>;
  };

  // Knowledge Base
  knowledgeBase: {
    searchArticles: (query: string, categoryId?: string) => Promise<ApiResponse<SearchResult<KnowledgeBaseArticle>>>;
    getArticle: (articleId: string) => Promise<ApiResponse<KnowledgeBaseArticle>>;
    getCategories: () => Promise<ApiResponse<KnowledgeBaseCategory[]>>;
    getFeaturedArticles: (limit?: number) => Promise<ApiResponse<KnowledgeBaseArticle[]>>;
    getPopularArticles: (limit?: number) => Promise<ApiResponse<KnowledgeBaseArticle[]>>;
    voteArticle: (articleId: string, helpful: boolean) => Promise<ApiResponse<void>>;
    rateArticle: (articleId: string, rating: number) => Promise<ApiResponse<void>>;
    trackView: (articleId: string) => void;
  };

  // File Upload
  fileUpload: {
    upload: (files: File[], config?: Partial<FileUploadConfig>) => Promise<ApiResponse<UploadedFile[]>>;
    uploadSingle: (file: File, config?: Partial<FileUploadConfig>) => Promise<ApiResponse<UploadedFile>>;
    getUploadProgress: (uploadId: string) => number;
    cancelUpload: (uploadId: string) => void;
    deleteFile: (fileId: string) => Promise<ApiResponse<void>>;
    getFileInfo: (fileId: string) => Promise<ApiResponse<UploadedFile>>;
  };

  // Analytics & Metrics
  analytics: {
    getMetrics: (period: { startDate: string; endDate: string }) => Promise<ApiResponse<SupportMetrics>>;
    getTicketTrends: (period: string) => Promise<ApiResponse<unknown>>;
    getChatMetrics: (period: string) => Promise<ApiResponse<unknown>>;
    getKBMetrics: (period: string) => Promise<ApiResponse<unknown>>;
    exportData: (type: 'tickets' | 'chats' | 'kb', format: 'csv' | 'xlsx') => Promise<ApiResponse<string>>;
  };

  // Real-time Operations
  realtime: {
    subscribe: (entityType: string, entityId: string, callback: (data: unknown) => void) => () => void;
    isConnected: boolean;
    connectionStatus: 'connecting' | 'connected' | 'disconnected' | 'error';
  };

  // State Management
  state: {
    isLoading: (operation?: string) => boolean;
    hasError: (operation?: string) => boolean;
    getError: (operation?: string) => string | null;
    clearError: (operation?: string) => void;
  };

  // Utility Functions
  utils: {
    formatTimestamp: (timestamp: string) => string;
    calculateSLA: (ticket: SupportTicket) => { breached: boolean; timeRemaining?: number };
    validateFileUpload: (file: File, config: FileUploadConfig) => string | null;
    generateTicketNumber: () => string;
    sanitizeContent: (content: string) => string;
  };
}

// ===== MAIN HOOK =====

export function useSupportOperations(config: SupportOperationsConfig): UseSupportOperationsReturn {
  const queryClient = useQueryClient();
  const [isInitialized, setIsInitialized] = useState(false);
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>({});
  const [errorStates, setErrorStates] = useState<Record<string, string | null>>({});
  const [activeUploads, setActiveUploads] = useState<Map<string, number>>(new Map());
  const [realtimeConnection, setRealtimeConnection] = useState<{
    isConnected: boolean;
    status: 'connecting' | 'connected' | 'disconnected' | 'error';
    socket?: WebSocket;
  }>({ isConnected: false, status: 'disconnected' });

  const activeSessionRef = useRef<ChatSession | null>(null);

  // ===== INITIALIZATION =====

  useEffect(() => {
    const initialize = async () => {
      try {
        // Initialize real-time connection if enabled
        if (config.enableRealtime) {
          initializeRealtimeConnection();
        }

        setIsInitialized(true);
      } catch (error) {
        console.error('[SupportOperations] Initialization failed:', error);
        setErrorStates(prev => ({ ...prev, initialization: 'Failed to initialize support system' }));
      }
    };

    initialize();

    return () => {
      // Cleanup
      if (realtimeConnection.socket) {
        realtimeConnection.socket.close();
      }
    };
  }, [config]);

  // ===== REAL-TIME CONNECTION =====

  const initializeRealtimeConnection = useCallback(() => {
    const wsUrl = `${config.baseUrl.replace('http', 'ws')}/ws/support`;
    const socket = new WebSocket(wsUrl);

    setRealtimeConnection(prev => ({ ...prev, status: 'connecting' }));

    socket.onopen = () => {
      setRealtimeConnection(prev => ({
        ...prev,
        isConnected: true,
        status: 'connected',
        socket
      }));
    };

    socket.onclose = () => {
      setRealtimeConnection(prev => ({
        ...prev,
        isConnected: false,
        status: 'disconnected',
        socket: undefined
      }));
    };

    socket.onerror = () => {
      setRealtimeConnection(prev => ({
        ...prev,
        isConnected: false,
        status: 'error'
      }));
    };
  }, [config.baseUrl]);

  // ===== UTILITY FUNCTIONS =====

  const setLoading = useCallback((operation: string, loading: boolean) => {
    setLoadingStates(prev => ({ ...prev, [operation]: loading }));
  }, []);

  const setError = useCallback((operation: string, error: string | null) => {
    setErrorStates(prev => ({ ...prev, [operation]: error }));
  }, []);

  const apiRequest = useCallback(async <T>(
    method: string,
    endpoint: string,
    data?: unknown,
    operation?: string
  ): Promise<ApiResponse<T>> => {
    if (operation) {
      setLoading(operation, true);
      setError(operation, null);
    }

    try {
      const url = `${config.baseUrl}${config.apiVersion || '/api/v1'}${endpoint}`;
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'X-Portal-Type': config.portalType,
        },
        body: data ? JSON.stringify(data) : undefined,
        signal: AbortSignal.timeout(config.timeout || 30000),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Request failed');
      }

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      if (operation) {
        setError(operation, errorMessage);
      }
      return { success: false, error: errorMessage };
    } finally {
      if (operation) {
        setLoading(operation, false);
      }
    }
  }, [config]);

  // ===== SUPPORT TICKETS =====

  const tickets = {
    list: useCallback(async (filters?: SearchFilters) => {
      return apiRequest<PaginatedResponse<SupportTicket>>('GET', '/tickets', filters, 'tickets.list');
    }, [apiRequest]),

    get: useCallback(async (ticketId: string) => {
      return apiRequest<SupportTicket>('GET', `/tickets/${ticketId}`, undefined, 'tickets.get');
    }, [apiRequest]),

    create: useCallback(async (ticketData: Partial<SupportTicket>) => {
      const result = await apiRequest<SupportTicket>('POST', '/tickets', ticketData, 'tickets.create');
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['tickets'] });
      }
      return result;
    }, [apiRequest, queryClient]),

    update: useCallback(async (ticketId: string, updates: Partial<SupportTicket>) => {
      const result = await apiRequest<SupportTicket>('PATCH', `/tickets/${ticketId}`, updates, 'tickets.update');
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['tickets', ticketId] });
        queryClient.invalidateQueries({ queryKey: ['tickets'] });
      }
      return result;
    }, [apiRequest, queryClient]),

    addMessage: useCallback(async (ticketId: string, message: string, attachments?: File[]) => {
      const formData = new FormData();
      formData.append('message', message);

      if (attachments) {
        attachments.forEach(file => {
          formData.append('attachments', file);
        });
      }

      const result = await apiRequest<void>('POST', `/tickets/${ticketId}/messages`, formData, 'tickets.addMessage');
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['tickets', ticketId] });
      }
      return result;
    }, [apiRequest, queryClient]),

    changeStatus: useCallback(async (ticketId: string, status: TicketStatus, reason?: string) => {
      const result = await apiRequest<void>('PATCH', `/tickets/${ticketId}/status`, { status, reason }, 'tickets.changeStatus');
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['tickets', ticketId] });
        queryClient.invalidateQueries({ queryKey: ['tickets'] });
      }
      return result;
    }, [apiRequest, queryClient]),

    assign: useCallback(async (ticketId: string, agentId: string) => {
      const result = await apiRequest<void>('PATCH', `/tickets/${ticketId}/assign`, { agentId }, 'tickets.assign');
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['tickets', ticketId] });
      }
      return result;
    }, [apiRequest, queryClient]),

    close: useCallback(async (ticketId: string, resolution?: string) => {
      const result = await apiRequest<void>('POST', `/tickets/${ticketId}/close`, { resolution }, 'tickets.close');
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['tickets', ticketId] });
        queryClient.invalidateQueries({ queryKey: ['tickets'] });
      }
      return result;
    }, [apiRequest, queryClient]),

    search: useCallback(async (query: string, filters?: SearchFilters) => {
      return apiRequest<SearchResult<SupportTicket>>('POST', '/tickets/search', { query, filters }, 'tickets.search');
    }, [apiRequest])
  };

  // ===== LIVE CHAT =====

  const chat = {
    startSession: useCallback(async (customerId?: string) => {
      const result = await apiRequest<ChatSession>('POST', '/chat/sessions', { customerId }, 'chat.startSession');
      if (result.success && result.data) {
        activeSessionRef.current = result.data;
      }
      return result;
    }, [apiRequest]),

    endSession: useCallback(async (sessionId: string) => {
      const result = await apiRequest<void>('POST', `/chat/sessions/${sessionId}/end`, undefined, 'chat.endSession');
      if (result.success && activeSessionRef.current?.sessionId === sessionId) {
        activeSessionRef.current = null;
      }
      return result;
    }, [apiRequest]),

    sendMessage: useCallback(async (sessionId: string, message: string, attachments?: File[]) => {
      const formData = new FormData();
      formData.append('message', message);

      if (attachments) {
        attachments.forEach(file => {
          formData.append('attachments', file);
        });
      }

      const result = await apiRequest<ChatMessage>('POST', `/chat/sessions/${sessionId}/messages`, formData, 'chat.sendMessage');
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['chat', sessionId, 'messages'] });
      }
      return result;
    }, [apiRequest, queryClient]),

    getMessages: useCallback(async (sessionId: string, limit = 50, before?: string) => {
      return apiRequest<ChatMessage[]>('GET', `/chat/sessions/${sessionId}/messages?limit=${limit}${before ? `&before=${before}` : ''}`, undefined, 'chat.getMessages');
    }, [apiRequest]),

    transferToAgent: useCallback(async (sessionId: string, agentId: string, reason?: string) => {
      const result = await apiRequest<void>('POST', `/chat/sessions/${sessionId}/transfer`, { agentId, reason }, 'chat.transfer');
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['chat', sessionId] });
      }
      return result;
    }, [apiRequest, queryClient]),

    setTyping: useCallback((sessionId: string, isTyping: boolean) => {
      if (realtimeConnection.socket && realtimeConnection.isConnected) {
        realtimeConnection.socket.send(JSON.stringify({
          type: 'typing',
          sessionId,
          isTyping
        }));
      }
    }, [realtimeConnection]),

    getActiveSession: useCallback(() => activeSessionRef.current, []),

    getSessionHistory: useCallback(async (customerId: string) => {
      return apiRequest<ChatSession[]>('GET', `/chat/sessions?customerId=${customerId}`, undefined, 'chat.getHistory');
    }, [apiRequest])
  };

  // ===== KNOWLEDGE BASE =====

  const knowledgeBase = {
    searchArticles: useCallback(async (query: string, categoryId?: string) => {
      return apiRequest<SearchResult<KnowledgeBaseArticle>>('POST', '/kb/search', { query, categoryId }, 'kb.search');
    }, [apiRequest]),

    getArticle: useCallback(async (articleId: string) => {
      return apiRequest<KnowledgeBaseArticle>('GET', `/kb/articles/${articleId}`, undefined, 'kb.getArticle');
    }, [apiRequest]),

    getCategories: useCallback(async () => {
      return apiRequest<KnowledgeBaseCategory[]>('GET', '/kb/categories', undefined, 'kb.getCategories');
    }, [apiRequest]),

    getFeaturedArticles: useCallback(async (limit = 10) => {
      return apiRequest<KnowledgeBaseArticle[]>('GET', `/kb/articles/featured?limit=${limit}`, undefined, 'kb.getFeatured');
    }, [apiRequest]),

    getPopularArticles: useCallback(async (limit = 10) => {
      return apiRequest<KnowledgeBaseArticle[]>('GET', `/kb/articles/popular?limit=${limit}`, undefined, 'kb.getPopular');
    }, [apiRequest]),

    voteArticle: useCallback(async (articleId: string, helpful: boolean) => {
      const result = await apiRequest<void>('POST', `/kb/articles/${articleId}/vote`, { helpful }, 'kb.vote');
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['kb', articleId] });
      }
      return result;
    }, [apiRequest, queryClient]),

    rateArticle: useCallback(async (articleId: string, rating: number) => {
      const result = await apiRequest<void>('POST', `/kb/articles/${articleId}/rate`, { rating }, 'kb.rate');
      if (result.success) {
        queryClient.invalidateQueries({ queryKey: ['kb', articleId] });
      }
      return result;
    }, [apiRequest, queryClient]),

    trackView: useCallback((articleId: string) => {
      // Track article view asynchronously without blocking UI
      apiRequest<void>('POST', `/kb/articles/${articleId}/view`, undefined);
    }, [apiRequest])
  };

  // ===== FILE UPLOAD =====

  const fileUpload = {
    upload: useCallback(async (files: File[], uploadConfig?: Partial<FileUploadConfig>) => {
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });

      if (uploadConfig) {
        formData.append('config', JSON.stringify(uploadConfig));
      }

      return apiRequest<UploadedFile[]>('POST', '/files/upload', formData, 'files.upload');
    }, [apiRequest]),

    uploadSingle: useCallback(async (file: File, uploadConfig?: Partial<FileUploadConfig>) => {
      const formData = new FormData();
      formData.append('file', file);

      if (uploadConfig) {
        formData.append('config', JSON.stringify(uploadConfig));
      }

      return apiRequest<UploadedFile>('POST', '/files/upload/single', formData, 'files.uploadSingle');
    }, [apiRequest]),

    getUploadProgress: useCallback((uploadId: string) => {
      return activeUploads.get(uploadId) || 0;
    }, [activeUploads]),

    cancelUpload: useCallback((uploadId: string) => {
      // Implementation would depend on upload mechanism
      setActiveUploads(prev => {
        const newMap = new Map(prev);
        newMap.delete(uploadId);
        return newMap;
      });
    }, []),

    deleteFile: useCallback(async (fileId: string) => {
      return apiRequest<void>('DELETE', `/files/${fileId}`, undefined, 'files.delete');
    }, [apiRequest]),

    getFileInfo: useCallback(async (fileId: string) => {
      return apiRequest<UploadedFile>('GET', `/files/${fileId}`, undefined, 'files.getInfo');
    }, [apiRequest])
  };

  // ===== ANALYTICS =====

  const analytics = {
    getMetrics: useCallback(async (period: { startDate: string; endDate: string }) => {
      return apiRequest<SupportMetrics>('POST', '/analytics/metrics', period, 'analytics.getMetrics');
    }, [apiRequest]),

    getTicketTrends: useCallback(async (period: string) => {
      return apiRequest<unknown>('GET', `/analytics/tickets/trends?period=${period}`, undefined, 'analytics.getTicketTrends');
    }, [apiRequest]),

    getChatMetrics: useCallback(async (period: string) => {
      return apiRequest<unknown>('GET', `/analytics/chat/metrics?period=${period}`, undefined, 'analytics.getChatMetrics');
    }, [apiRequest]),

    getKBMetrics: useCallback(async (period: string) => {
      return apiRequest<unknown>('GET', `/analytics/kb/metrics?period=${period}`, undefined, 'analytics.getKBMetrics');
    }, [apiRequest]),

    exportData: useCallback(async (type: 'tickets' | 'chats' | 'kb', format: 'csv' | 'xlsx') => {
      return apiRequest<string>('POST', '/analytics/export', { type, format }, 'analytics.export');
    }, [apiRequest])
  };

  // ===== REAL-TIME =====

  const realtime = {
    subscribe: useCallback((entityType: string, entityId: string, callback: (data: unknown) => void) => {
      if (!realtimeConnection.socket || !realtimeConnection.isConnected) {
        return () => {}; // No-op unsubscribe
      }

      const subscription = { entityType, entityId };
      realtimeConnection.socket.send(JSON.stringify({
        type: 'subscribe',
        ...subscription
      }));

      const handleMessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          if (data.entityType === entityType && data.entityId === entityId) {
            callback(data);
          }
        } catch (error) {
          console.error('[SupportOperations] Failed to parse real-time message:', error);
        }
      };

      realtimeConnection.socket.addEventListener('message', handleMessage);

      // Return unsubscribe function
      return () => {
        if (realtimeConnection.socket) {
          realtimeConnection.socket.removeEventListener('message', handleMessage);
          realtimeConnection.socket.send(JSON.stringify({
            type: 'unsubscribe',
            ...subscription
          }));
        }
      };
    }, [realtimeConnection]),

    isConnected: realtimeConnection.isConnected,
    connectionStatus: realtimeConnection.status
  };

  // ===== STATE MANAGEMENT =====

  const state = {
    isLoading: useCallback((operation?: string) => {
      if (operation) {
        return loadingStates[operation] || false;
      }
      return Object.values(loadingStates).some(Boolean);
    }, [loadingStates]),

    hasError: useCallback((operation?: string) => {
      if (operation) {
        return errorStates[operation] !== null && errorStates[operation] !== undefined;
      }
      return Object.values(errorStates).some(error => error !== null);
    }, [errorStates]),

    getError: useCallback((operation?: string) => {
      if (operation) {
        return errorStates[operation] || null;
      }
      const errors = Object.values(errorStates).filter(error => error !== null);
      return errors[0] || null;
    }, [errorStates]),

    clearError: useCallback((operation?: string) => {
      if (operation) {
        setErrorStates(prev => ({ ...prev, [operation]: null }));
      } else {
        setErrorStates({});
      }
    }, [])
  };

  // ===== UTILITY FUNCTIONS =====

  const utils = {
    formatTimestamp: useCallback((timestamp: string) => {
      const date = new Date(timestamp);
      const now = new Date();
      const diffHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));

      if (diffHours < 24) {
        return date.toLocaleTimeString('en-US', {
          hour: 'numeric',
          minute: '2-digit',
          hour12: true,
        });
      }

      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    }, []),

    calculateSLA: useCallback((ticket: SupportTicket) => {
      const slaHours = ticket.priority === 'critical' ? 2 :
                     ticket.priority === 'high' ? 8 :
                     ticket.priority === 'medium' ? 24 : 72;

      const createdAt = new Date(ticket.createdAt);
      const now = new Date();
      const hoursElapsed = (now.getTime() - createdAt.getTime()) / (1000 * 60 * 60);

      return {
        breached: hoursElapsed > slaHours,
        timeRemaining: Math.max(0, slaHours - hoursElapsed)
      };
    }, []),

    validateFileUpload: useCallback((file: File, fileConfig: FileUploadConfig) => {
      if (file.size > fileConfig.maxFileSize) {
        return `File size exceeds maximum allowed size of ${fileConfig.maxFileSize} bytes`;
      }

      if (fileConfig.acceptedFileTypes.length > 0 && !fileConfig.acceptedFileTypes.includes(file.type)) {
        return `File type ${file.type} is not allowed`;
      }

      if (fileConfig.customValidation) {
        return fileConfig.customValidation(file);
      }

      return null;
    }, []),

    generateTicketNumber: useCallback(() => {
      const date = new Date();
      const year = date.getFullYear();
      const month = (date.getMonth() + 1).toString().padStart(2, '0');
      const randomNum = Math.floor(Math.random() * 10000).toString().padStart(4, '0');
      return `TKT-${year}${month}-${randomNum}`;
    }, []),

    sanitizeContent: useCallback((content: string) => {
      // Basic HTML sanitization - in production, use a proper sanitization library
      return content
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
        .replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '')
        .replace(/javascript:/gi, '');
    }, [])
  };

  return {
    config,
    isInitialized,
    tickets,
    chat,
    knowledgeBase,
    fileUpload,
    analytics,
    realtime,
    state,
    utils
  };
}
