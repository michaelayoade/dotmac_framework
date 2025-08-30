import { useState, useEffect, useCallback, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';
import { useApiClient } from '@dotmac/headless';

import type {
  UseCollaborationOptions,
  UseCollaborationResult,
  Document,
  CollaborationUser,
  Comment,
  Suggestion,
  Operation,
  Conflict,
  CursorPosition,
  TextSelection,
  CollaborationEvent,
  EventType,
  UserStatus,
  ConflictResolutionStrategy,
  CollaborationError,
  CollaborationErrorCode
} from '../types';

const API_ENDPOINTS = {
  DOCUMENTS: '/api/collaboration/documents',
  COMMENTS: '/api/collaboration/comments',
  SUGGESTIONS: '/api/collaboration/suggestions',
  OPERATIONS: '/api/collaboration/operations',
  PRESENCE: '/api/collaboration/presence'
} as const;

export function useCollaboration(options: UseCollaborationOptions): UseCollaborationResult {
  const {
    document_id,
    user,
    websocket_url = '/collaboration',
    auto_save = true,
    auto_save_interval = 5000,
    conflict_resolution = ConflictResolutionStrategy.MERGE_CHANGES,
    enable_presence = true,
    enable_comments = true,
    enable_suggestions = true
  } = options;

  // State
  const [document, setDocument] = useState<Document | null>(null);
  const [content, setContent] = useState<string>('');
  const [version, setVersion] = useState<number>(0);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(true);
  const [conflicts, setConflicts] = useState<Conflict[]>([]);
  const [users, setUsers] = useState<CollaborationUser[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Refs
  const socketRef = useRef<Socket | null>(null);
  const yDocRef = useRef<Y.Doc | null>(null);
  const yProviderRef = useRef<WebsocketProvider | null>(null);
  const yTextRef = useRef<Y.Text | null>(null);
  const autoSaveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const operationsBufferRef = useRef<Operation[]>([]);
  const lastSavedVersionRef = useRef<number>(0);

  const apiClient = useApiClient();

  // Initialize Yjs document and WebSocket connection
  useEffect(() => {
    const initializeCollaboration = async () => {
      try {
        setConnecting(true);
        setError(null);

        // Create Yjs document
        const yDoc = new Y.Doc();
        const yText = yDoc.getText('content');
        yDocRef.current = yDoc;
        yTextRef.current = yText;

        // Set up WebSocket provider for Yjs
        const wsProvider = new WebsocketProvider(
          websocket_url,
          `doc-${document_id}`,
          yDoc,
          {
            params: {
              userId: user.id,
              tenantId: user.tenant_id
            }
          }
        );
        yProviderRef.current = wsProvider;

        // Set up Socket.io for real-time events
        const socket = io(websocket_url, {
          query: {
            document_id,
            user_id: user.id,
            tenant_id: user.tenant_id
          }
        });
        socketRef.current = socket;

        // Socket event handlers
        socket.on('connect', () => {
          setConnected(true);
          setConnecting(false);
          console.log(`Connected to collaboration server for document ${document_id}`);
        });

        socket.on('disconnect', () => {
          setConnected(false);
          console.log(`Disconnected from collaboration server for document ${document_id}`);
        });

        socket.on('error', (err: any) => {
          setError(err.message || 'Connection error');
          setConnecting(false);
        });

        // Handle collaboration events
        socket.on('collaboration_event', handleCollaborationEvent);
        socket.on('user_joined', handleUserJoined);
        socket.on('user_left', handleUserLeft);
        socket.on('user_presence', handleUserPresence);
        socket.on('comment_added', handleCommentEvent);
        socket.on('suggestion_added', handleSuggestionEvent);
        socket.on('conflict_detected', handleConflictDetected);

        // Yjs event handlers
        yText.observe(handleYjsTextChange);
        yDoc.on('update', handleYjsDocUpdate);

        // Load initial document data
        await loadDocument();
        await loadComments();
        await loadSuggestions();

        // Join collaboration session
        socket.emit('join_document', {
          document_id,
          user_id: user.id,
          tenant_id: user.tenant_id
        });

      } catch (err) {
        console.error('Failed to initialize collaboration:', err);
        setError(err instanceof Error ? err.message : 'Initialization failed');
        setConnecting(false);
      }
    };

    initializeCollaboration();

    // Cleanup on unmount
    return () => {
      if (socketRef.current) {
        socketRef.current.emit('leave_document', { document_id, user_id: user.id });
        socketRef.current.disconnect();
      }
      if (yProviderRef.current) {
        yProviderRef.current.destroy();
      }
      if (yDocRef.current) {
        yDocRef.current.destroy();
      }
      if (autoSaveTimerRef.current) {
        clearInterval(autoSaveTimerRef.current);
      }
    };
  }, [document_id, user.id, websocket_url]);

  // Auto-save functionality
  useEffect(() => {
    if (!auto_save || !connected) return;

    autoSaveTimerRef.current = setInterval(async () => {
      if (!saved && version > lastSavedVersionRef.current) {
        await saveDocument();
      }
    }, auto_save_interval);

    return () => {
      if (autoSaveTimerRef.current) {
        clearInterval(autoSaveTimerRef.current);
      }
    };
  }, [auto_save, auto_save_interval, connected, saved, version]);

  // Load document data
  const loadDocument = useCallback(async (): Promise<void> => {
    try {
      const response = await apiClient.get<Document>(`${API_ENDPOINTS.DOCUMENTS}/${document_id}`);
      const doc = response.data;

      setDocument(doc);
      setContent(doc.content);
      setVersion(doc.version);
      lastSavedVersionRef.current = doc.version;

      // Initialize Yjs text with document content
      if (yTextRef.current && yTextRef.current.length === 0) {
        yTextRef.current.insert(0, doc.content);
      }
    } catch (err) {
      throw new CollaborationError(
        'Failed to load document',
        CollaborationErrorCode.DOCUMENT_NOT_FOUND,
        document_id,
        user.id
      );
    }
  }, [apiClient, document_id, user.id]);

  // Load comments
  const loadComments = useCallback(async (): Promise<void> => {
    if (!enable_comments) return;

    try {
      const response = await apiClient.get<{ comments: Comment[] }>(
        `${API_ENDPOINTS.COMMENTS}?document_id=${document_id}`
      );
      setComments(response.data.comments);
    } catch (err) {
      console.warn('Failed to load comments:', err);
    }
  }, [apiClient, document_id, enable_comments]);

  // Load suggestions
  const loadSuggestions = useCallback(async (): Promise<void> => {
    if (!enable_suggestions) return;

    try {
      const response = await apiClient.get<{ suggestions: Suggestion[] }>(
        `${API_ENDPOINTS.SUGGESTIONS}?document_id=${document_id}`
      );
      setSuggestions(response.data.suggestions);
    } catch (err) {
      console.warn('Failed to load suggestions:', err);
    }
  }, [apiClient, document_id, enable_suggestions]);

  // Event handlers
  const handleCollaborationEvent = useCallback((event: CollaborationEvent) => {
    console.log('Collaboration event received:', event);

    // Handle different event types
    switch (event.type) {
      case EventType.DOCUMENT_SAVED:
        setSaved(true);
        if (event.data.version) {
          setVersion(event.data.version);
          lastSavedVersionRef.current = event.data.version;
        }
        break;

      case EventType.DOCUMENT_LOCKED:
        if (document) {
          setDocument({
            ...document,
            metadata: {
              ...document.metadata,
              locked: true,
              locked_by: event.data.locked_by,
              locked_at: event.timestamp
            }
          });
        }
        break;

      case EventType.DOCUMENT_UNLOCKED:
        if (document) {
          setDocument({
            ...document,
            metadata: {
              ...document.metadata,
              locked: false,
              locked_by: undefined,
              locked_at: undefined
            }
          });
        }
        break;
    }
  }, [document]);

  const handleUserJoined = useCallback((userData: CollaborationUser) => {
    setUsers(prev => {
      const existing = prev.find(u => u.id === userData.id);
      if (existing) {
        return prev.map(u => u.id === userData.id ? { ...u, ...userData } : u);
      }
      return [...prev, userData];
    });
  }, []);

  const handleUserLeft = useCallback((userData: { user_id: string }) => {
    setUsers(prev => prev.filter(u => u.id !== userData.user_id));
  }, []);

  const handleUserPresence = useCallback((presenceData: {
    user_id: string;
    cursor?: CursorPosition;
    selection?: TextSelection;
    status: UserStatus;
  }) => {
    if (!enable_presence) return;

    setUsers(prev => prev.map(u =>
      u.id === presenceData.user_id
        ? {
            ...u,
            cursor: presenceData.cursor,
            selection: presenceData.selection,
            status: presenceData.status,
            last_seen: new Date().toISOString()
          }
        : u
    ));
  }, [enable_presence]);

  const handleCommentEvent = useCallback((commentData: {
    action: string;
    comment: Comment;
  }) => {
    if (!enable_comments) return;

    switch (commentData.action) {
      case 'add':
        setComments(prev => [...prev, commentData.comment]);
        break;
      case 'update':
        setComments(prev => prev.map(c =>
          c.id === commentData.comment.id ? commentData.comment : c
        ));
        break;
      case 'delete':
        setComments(prev => prev.filter(c => c.id !== commentData.comment.id));
        break;
      case 'resolve':
        setComments(prev => prev.map(c =>
          c.id === commentData.comment.id
            ? { ...c, resolved: true, resolved_by: user.id, resolved_at: new Date().toISOString() }
            : c
        ));
        break;
    }
  }, [enable_comments, user.id]);

  const handleSuggestionEvent = useCallback((suggestionData: {
    action: string;
    suggestion: Suggestion;
  }) => {
    if (!enable_suggestions) return;

    switch (suggestionData.action) {
      case 'add':
        setSuggestions(prev => [...prev, suggestionData.suggestion]);
        break;
      case 'accept':
      case 'reject':
      case 'withdraw':
        setSuggestions(prev => prev.map(s =>
          s.id === suggestionData.suggestion.id ? suggestionData.suggestion : s
        ));
        break;
    }
  }, [enable_suggestions]);

  const handleConflictDetected = useCallback((conflictData: Conflict) => {
    setConflicts(prev => [...prev, conflictData]);
    console.warn('Conflict detected:', conflictData);
  }, []);

  const handleYjsTextChange = useCallback((event: Y.YTextEvent, transaction: Y.Transaction) => {
    if (transaction.origin === 'self') return; // Skip self-generated changes

    const newContent = yTextRef.current?.toString() || '';
    setContent(newContent);
    setSaved(false);
    setVersion(prev => prev + 1);
  }, []);

  const handleYjsDocUpdate = useCallback((update: Uint8Array, origin: any, doc: Y.Doc) => {
    // Handle document updates for conflict resolution and syncing
    console.log('Yjs document updated');
  }, []);

  // Actions
  const updateContent = useCallback((newContent: string): void => {
    if (!yTextRef.current) return;

    const yText = yTextRef.current;
    const currentContent = yText.toString();

    if (currentContent !== newContent) {
      // Apply the change to Yjs document
      yText.delete(0, currentContent.length);
      yText.insert(0, newContent);

      setContent(newContent);
      setSaved(false);
      setVersion(prev => prev + 1);
    }
  }, []);

  const saveDocument = useCallback(async (): Promise<void> => {
    if (!document || saving) return;

    try {
      setSaving(true);
      setError(null);

      const updatedDocument = {
        ...document,
        content,
        version: version + 1,
        updated_at: new Date().toISOString(),
        metadata: {
          ...document.metadata,
          last_saved: new Date().toISOString(),
          word_count: content.split(/\s+/).length,
          character_count: content.length
        }
      };

      const response = await apiClient.put<Document>(
        `${API_ENDPOINTS.DOCUMENTS}/${document_id}`,
        updatedDocument
      );

      setDocument(response.data);
      setVersion(response.data.version);
      lastSavedVersionRef.current = response.data.version;
      setSaved(true);

      // Emit save event
      if (socketRef.current) {
        socketRef.current.emit('document_saved', {
          document_id,
          version: response.data.version,
          user_id: user.id
        });
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save document';
      setError(errorMessage);
      throw new CollaborationError(
        errorMessage,
        CollaborationErrorCode.SAVE_FAILED,
        document_id,
        user.id
      );
    } finally {
      setSaving(false);
    }
  }, [apiClient, document, document_id, content, version, user.id]);

  const addComment = useCallback(async (
    commentData: Omit<Comment, 'id' | 'created_at' | 'author'>
  ): Promise<Comment> => {
    if (!enable_comments) {
      throw new CollaborationError(
        'Comments are not enabled',
        CollaborationErrorCode.OPERATION_FAILED,
        document_id,
        user.id
      );
    }

    try {
      const newComment = {
        ...commentData,
        document_id,
        author: {
          ...user,
          status: UserStatus.ONLINE,
          last_seen: new Date().toISOString(),
          permissions: { read: true, write: true, comment: true, suggest: true, admin: false }
        } as CollaborationUser
      };

      const response = await apiClient.post<Comment>(API_ENDPOINTS.COMMENTS, newComment);
      const comment = response.data;

      setComments(prev => [...prev, comment]);

      // Emit comment event
      if (socketRef.current) {
        socketRef.current.emit('comment_added', {
          document_id,
          comment,
          user_id: user.id
        });
      }

      return comment;
    } catch (err) {
      throw new CollaborationError(
        'Failed to add comment',
        CollaborationErrorCode.OPERATION_FAILED,
        document_id,
        user.id
      );
    }
  }, [apiClient, document_id, user, enable_comments]);

  const resolveComment = useCallback(async (comment_id: string): Promise<void> => {
    try {
      await apiClient.patch(`${API_ENDPOINTS.COMMENTS}/${comment_id}`, {
        resolved: true,
        resolved_by: user.id,
        resolved_at: new Date().toISOString()
      });

      setComments(prev => prev.map(c =>
        c.id === comment_id
          ? { ...c, resolved: true, resolved_by: user.id, resolved_at: new Date().toISOString() }
          : c
      ));

      // Emit resolve event
      if (socketRef.current) {
        socketRef.current.emit('comment_resolved', {
          document_id,
          comment_id,
          user_id: user.id
        });
      }

    } catch (err) {
      throw new CollaborationError(
        'Failed to resolve comment',
        CollaborationErrorCode.OPERATION_FAILED,
        document_id,
        user.id
      );
    }
  }, [apiClient, document_id, user.id]);

  const addSuggestion = useCallback(async (
    suggestionData: Omit<Suggestion, 'id' | 'created_at' | 'author' | 'status'>
  ): Promise<Suggestion> => {
    if (!enable_suggestions) {
      throw new CollaborationError(
        'Suggestions are not enabled',
        CollaborationErrorCode.OPERATION_FAILED,
        document_id,
        user.id
      );
    }

    try {
      const newSuggestion = {
        ...suggestionData,
        document_id,
        author: {
          ...user,
          status: UserStatus.ONLINE,
          last_seen: new Date().toISOString(),
          permissions: { read: true, write: true, comment: true, suggest: true, admin: false }
        } as CollaborationUser,
        status: 'pending' as const
      };

      const response = await apiClient.post<Suggestion>(API_ENDPOINTS.SUGGESTIONS, newSuggestion);
      const suggestion = response.data;

      setSuggestions(prev => [...prev, suggestion]);

      // Emit suggestion event
      if (socketRef.current) {
        socketRef.current.emit('suggestion_added', {
          document_id,
          suggestion,
          user_id: user.id
        });
      }

      return suggestion;
    } catch (err) {
      throw new CollaborationError(
        'Failed to add suggestion',
        CollaborationErrorCode.OPERATION_FAILED,
        document_id,
        user.id
      );
    }
  }, [apiClient, document_id, user, enable_suggestions]);

  const acceptSuggestion = useCallback(async (suggestion_id: string): Promise<void> => {
    try {
      const suggestion = suggestions.find(s => s.id === suggestion_id);
      if (!suggestion) return;

      // Apply the suggestion to the document content
      const beforeText = content.substring(0, suggestion.position.start);
      const afterText = content.substring(suggestion.position.end);
      const newContent = beforeText + suggestion.suggested_text + afterText;

      updateContent(newContent);

      // Update suggestion status
      await apiClient.patch(`${API_ENDPOINTS.SUGGESTIONS}/${suggestion_id}`, {
        status: 'accepted',
        reviewed_by: user.id,
        reviewed_at: new Date().toISOString()
      });

      setSuggestions(prev => prev.map(s =>
        s.id === suggestion_id
          ? { ...s, status: 'accepted' as const, reviewed_by: user.id, reviewed_at: new Date().toISOString() }
          : s
      ));

      // Emit accept event
      if (socketRef.current) {
        socketRef.current.emit('suggestion_accepted', {
          document_id,
          suggestion_id,
          user_id: user.id
        });
      }

    } catch (err) {
      throw new CollaborationError(
        'Failed to accept suggestion',
        CollaborationErrorCode.OPERATION_FAILED,
        document_id,
        user.id
      );
    }
  }, [suggestions, content, updateContent, apiClient, document_id, user.id]);

  const rejectSuggestion = useCallback(async (suggestion_id: string): Promise<void> => {
    try {
      await apiClient.patch(`${API_ENDPOINTS.SUGGESTIONS}/${suggestion_id}`, {
        status: 'rejected',
        reviewed_by: user.id,
        reviewed_at: new Date().toISOString()
      });

      setSuggestions(prev => prev.map(s =>
        s.id === suggestion_id
          ? { ...s, status: 'rejected' as const, reviewed_by: user.id, reviewed_at: new Date().toISOString() }
          : s
      ));

      // Emit reject event
      if (socketRef.current) {
        socketRef.current.emit('suggestion_rejected', {
          document_id,
          suggestion_id,
          user_id: user.id
        });
      }

    } catch (err) {
      throw new CollaborationError(
        'Failed to reject suggestion',
        CollaborationErrorCode.OPERATION_FAILED,
        document_id,
        user.id
      );
    }
  }, [apiClient, document_id, user.id]);

  const updateCursor = useCallback((position: CursorPosition): void => {
    if (!enable_presence || !socketRef.current) return;

    socketRef.current.emit('cursor_update', {
      document_id,
      user_id: user.id,
      cursor: position
    });
  }, [document_id, user.id, enable_presence]);

  const updateSelection = useCallback((selection: TextSelection | null): void => {
    if (!enable_presence || !socketRef.current) return;

    socketRef.current.emit('selection_update', {
      document_id,
      user_id: user.id,
      selection
    });
  }, [document_id, user.id, enable_presence]);

  const lockDocument = useCallback(async (): Promise<void> => {
    try {
      await apiClient.post(`${API_ENDPOINTS.DOCUMENTS}/${document_id}/lock`, {
        user_id: user.id
      });

      if (document) {
        setDocument({
          ...document,
          metadata: {
            ...document.metadata,
            locked: true,
            locked_by: user.id,
            locked_at: new Date().toISOString()
          }
        });
      }

      // Emit lock event
      if (socketRef.current) {
        socketRef.current.emit('document_locked', {
          document_id,
          user_id: user.id
        });
      }

    } catch (err) {
      throw new CollaborationError(
        'Failed to lock document',
        CollaborationErrorCode.LOCK_FAILED,
        document_id,
        user.id
      );
    }
  }, [apiClient, document, document_id, user.id]);

  const unlockDocument = useCallback(async (): Promise<void> => {
    try {
      await apiClient.post(`${API_ENDPOINTS.DOCUMENTS}/${document_id}/unlock`, {
        user_id: user.id
      });

      if (document) {
        setDocument({
          ...document,
          metadata: {
            ...document.metadata,
            locked: false,
            locked_by: undefined,
            locked_at: undefined
          }
        });
      }

      // Emit unlock event
      if (socketRef.current) {
        socketRef.current.emit('document_unlocked', {
          document_id,
          user_id: user.id
        });
      }

    } catch (err) {
      throw new CollaborationError(
        'Failed to unlock document',
        CollaborationErrorCode.LOCK_FAILED,
        document_id,
        user.id
      );
    }
  }, [apiClient, document, document_id, user.id]);

  const resolveConflict = useCallback(async (
    conflict_id: string,
    resolution: ConflictResolutionStrategy
  ): Promise<void> => {
    try {
      await apiClient.post(`${API_ENDPOINTS.OPERATIONS}/conflicts/${conflict_id}/resolve`, {
        resolution,
        user_id: user.id
      });

      setConflicts(prev => prev.filter(c => c.id !== conflict_id));

      // Emit conflict resolution event
      if (socketRef.current) {
        socketRef.current.emit('conflict_resolved', {
          document_id,
          conflict_id,
          resolution,
          user_id: user.id
        });
      }

    } catch (err) {
      throw new CollaborationError(
        'Failed to resolve conflict',
        CollaborationErrorCode.CONFLICT_RESOLUTION_FAILED,
        document_id,
        user.id
      );
    }
  }, [apiClient, document_id, user.id]);

  return {
    // Document state
    document,
    content,
    version,
    saving,
    saved,
    conflicts,

    // Collaboration state
    users,
    comments,
    suggestions,

    // Connection state
    connected,
    connecting,
    error,

    // Actions
    updateContent,
    saveDocument,
    addComment,
    resolveComment,
    addSuggestion,
    acceptSuggestion,
    rejectSuggestion,
    updateCursor,
    updateSelection,
    lockDocument,
    unlockDocument,
    resolveConflict
  };
}
