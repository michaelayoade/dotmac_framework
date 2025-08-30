// Core collaboration types
export interface User {
  id: string;
  name: string;
  email?: string;
  avatar?: string;
  tenant_id?: string;
  metadata?: Record<string, any>;
}

export interface CollaborationUser extends User {
  cursor?: CursorPosition;
  selection?: TextSelection;
  color?: string;
  status: UserStatus;
  last_seen: string;
  permissions: UserPermissions;
}

export enum UserStatus {
  ONLINE = 'online',
  AWAY = 'away',
  BUSY = 'busy',
  TYPING = 'typing',
  IDLE = 'idle',
  OFFLINE = 'offline'
}

export interface UserPermissions {
  read: boolean;
  write: boolean;
  comment: boolean;
  suggest: boolean;
  admin: boolean;
}

export interface CursorPosition {
  x: number;
  y: number;
  line?: number;
  column?: number;
  visible: boolean;
  timestamp: string;
}

export interface TextSelection {
  start: number;
  end: number;
  direction?: 'forward' | 'backward';
  text?: string;
}

// Document and editing types
export interface Document {
  id: string;
  title: string;
  content: string;
  version: number;
  created_at: string;
  updated_at: string;
  owner_id: string;
  tenant_id?: string;
  permissions: DocumentPermissions;
  metadata: DocumentMetadata;
}

export interface DocumentPermissions {
  public_read: boolean;
  public_write: boolean;
  public_comment: boolean;
  users: Record<string, UserPermissions>;
  groups?: Record<string, UserPermissions>;
}

export interface DocumentMetadata {
  type: DocumentType;
  language?: string;
  tags: string[];
  folder_id?: string;
  locked: boolean;
  locked_by?: string;
  locked_at?: string;
  last_saved: string;
  auto_save: boolean;
  word_count?: number;
  character_count?: number;
}

export enum DocumentType {
  TEXT = 'text',
  MARKDOWN = 'markdown',
  CODE = 'code',
  JSON = 'json',
  YAML = 'yaml',
  HTML = 'html',
  RICH_TEXT = 'rich_text'
}

// Operation types for Operational Transform
export interface Operation {
  id: string;
  type: OperationType;
  data: OperationData;
  author: string;
  timestamp: string;
  version: number;
  applied: boolean;
}

export enum OperationType {
  INSERT = 'insert',
  DELETE = 'delete',
  RETAIN = 'retain',
  FORMAT = 'format',
  REPLACE = 'replace'
}

export interface OperationData {
  position: number;
  content?: string;
  length?: number;
  attributes?: Record<string, any>;
  oldContent?: string;
  newContent?: string;
}

// Real-time collaboration events
export interface CollaborationEvent {
  id: string;
  type: EventType;
  document_id: string;
  user_id: string;
  data: any;
  timestamp: string;
  tenant_id?: string;
}

export enum EventType {
  // Document events
  DOCUMENT_OPENED = 'document_opened',
  DOCUMENT_CLOSED = 'document_closed',
  DOCUMENT_SAVED = 'document_saved',
  DOCUMENT_LOCKED = 'document_locked',
  DOCUMENT_UNLOCKED = 'document_unlocked',

  // User events
  USER_JOINED = 'user_joined',
  USER_LEFT = 'user_left',
  USER_STATUS_CHANGED = 'user_status_changed',

  // Editing events
  TEXT_CHANGED = 'text_changed',
  CURSOR_MOVED = 'cursor_moved',
  SELECTION_CHANGED = 'selection_changed',

  // Comment events
  COMMENT_ADDED = 'comment_added',
  COMMENT_UPDATED = 'comment_updated',
  COMMENT_DELETED = 'comment_deleted',
  COMMENT_RESOLVED = 'comment_resolved',

  // Suggestion events
  SUGGESTION_ADDED = 'suggestion_added',
  SUGGESTION_ACCEPTED = 'suggestion_accepted',
  SUGGESTION_REJECTED = 'suggestion_rejected'
}

// Comments and suggestions
export interface Comment {
  id: string;
  document_id: string;
  author: CollaborationUser;
  content: string;
  position: CommentPosition;
  created_at: string;
  updated_at?: string;
  resolved: boolean;
  resolved_by?: string;
  resolved_at?: string;
  replies: CommentReply[];
  thread_id?: string;
}

export interface CommentPosition {
  line: number;
  column: number;
  selection?: TextSelection;
  context?: string;
}

export interface CommentReply {
  id: string;
  author: CollaborationUser;
  content: string;
  created_at: string;
  updated_at?: string;
}

export interface Suggestion {
  id: string;
  document_id: string;
  author: CollaborationUser;
  description?: string;
  position: TextSelection;
  original_text: string;
  suggested_text: string;
  status: SuggestionStatus;
  created_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
  comments: Comment[];
}

export enum SuggestionStatus {
  PENDING = 'pending',
  ACCEPTED = 'accepted',
  REJECTED = 'rejected',
  WITHDRAWN = 'withdrawn'
}

// Conflict resolution
export enum ConflictStatus {
  UNRESOLVED = 'unresolved',
  RESOLVED = 'resolved',
  REVIEWING = 'reviewing'
}

export interface Conflict {
  id: string;
  document_id: string;
  operations: Operation[];
  conflicting_operations: Operation[];
  resolution_strategy?: ConflictResolutionStrategy;
  status: ConflictStatus;
  resolved: boolean;
  resolved_by?: string;
  resolved_at?: string;
}

export enum ConflictResolutionStrategy {
  LAST_WRITER_WINS = 'last_writer_wins',
  FIRST_WRITER_WINS = 'first_writer_wins',
  MERGE_CHANGES = 'merge_changes',
  MANUAL_RESOLUTION = 'manual_resolution'
}

// Hooks and component props
export interface UseCollaborationOptions {
  document_id: string;
  user: User;
  websocket_url?: string;
  auto_save?: boolean;
  auto_save_interval?: number;
  conflict_resolution?: ConflictResolutionStrategy;
  enable_presence?: boolean;
  enable_comments?: boolean;
  enable_suggestions?: boolean;
}

export interface UseCollaborationResult {
  // Document state
  document: Document | null;
  content: string;
  version: number;
  saving: boolean;
  saved: boolean;
  conflicts: Conflict[];

  // Collaboration state
  users: CollaborationUser[];
  comments: Comment[];
  suggestions: Suggestion[];

  // Connection state
  connected: boolean;
  connecting: boolean;
  error: string | null;

  // Actions
  updateContent: (content: string) => void;
  saveDocument: () => Promise<void>;
  addComment: (comment: Omit<Comment, 'id' | 'created_at' | 'author'>) => Promise<Comment>;
  resolveComment: (comment_id: string) => Promise<void>;
  addSuggestion: (suggestion: Omit<Suggestion, 'id' | 'created_at' | 'author' | 'status'>) => Promise<Suggestion>;
  acceptSuggestion: (suggestion_id: string) => Promise<void>;
  rejectSuggestion: (suggestion_id: string) => Promise<void>;
  updateCursor: (position: CursorPosition) => void;
  updateSelection: (selection: TextSelection | null) => void;
  lockDocument: () => Promise<void>;
  unlockDocument: () => Promise<void>;
  resolveConflict: (conflict_id: string, resolution: ConflictResolutionStrategy) => Promise<void>;
}

export interface CollaborativeEditorProps {
  document_id: string;
  initial_content?: string;
  user: User;
  permissions?: UserPermissions;
  websocket_url?: string;
  auto_save?: boolean;
  auto_save_interval?: number;
  language?: string;
  theme?: 'light' | 'dark';
  show_presence?: boolean;
  show_comments?: boolean;
  show_suggestions?: boolean;
  show_line_numbers?: boolean;
  enable_minimap?: boolean;
  read_only?: boolean;
  on_save?: (document: Document) => void;
  on_error?: (error: Error) => void;
  on_user_join?: (user: CollaborationUser) => void;
  on_user_leave?: (user: CollaborationUser) => void;
}

export interface PresenceIndicatorProps {
  users: CollaborationUser[];
  current_user: User;
  max_avatars?: number;
  show_names?: boolean;
  show_status?: boolean;
  on_user_click?: (user: CollaborationUser) => void;
}

export interface CommentsPanelProps {
  comments: Comment[];
  current_user: User;
  document_id: string;
  on_add_comment?: (comment: Omit<Comment, 'id' | 'created_at' | 'author'>) => void;
  on_resolve_comment?: (comment_id: string) => void;
  on_reply_comment?: (comment_id: string, content: string) => void;
}

export interface SuggestionsPanelProps {
  suggestions: Suggestion[];
  current_user: User;
  document_id: string;
  on_accept_suggestion?: (suggestion_id: string) => void;
  on_reject_suggestion?: (suggestion_id: string) => void;
  on_add_comment?: (suggestion_id: string, content: string) => void;
}

export interface ConflictResolverProps {
  conflicts: Conflict[];
  document_id: string;
  current_user: User;
  on_resolve_conflict?: (conflict_id: string, resolution: ConflictResolutionStrategy) => void;
}

export interface DocumentHistoryProps {
  document_id: string;
  current_version: number;
  show_versions?: number;
  enable_restore?: boolean;
  on_version_select?: (version: number) => void;
  on_restore_version?: (version: number) => void;
}

// WebSocket message types
export interface WebSocketMessage {
  type: string;
  document_id: string;
  user_id: string;
  data: any;
  timestamp: string;
  tenant_id?: string;
}

export interface OperationMessage extends WebSocketMessage {
  type: 'operation';
  data: {
    operation: Operation;
  };
}

export interface PresenceMessage extends WebSocketMessage {
  type: 'presence';
  data: {
    cursor?: CursorPosition;
    selection?: TextSelection;
    status: UserStatus;
  };
}

export interface CommentMessage extends WebSocketMessage {
  type: 'comment';
  data: {
    action: 'add' | 'update' | 'delete' | 'resolve';
    comment: Comment;
  };
}

export interface SuggestionMessage extends WebSocketMessage {
  type: 'suggestion';
  data: {
    action: 'add' | 'accept' | 'reject' | 'withdraw';
    suggestion: Suggestion;
  };
}

export interface LockMessage extends WebSocketMessage {
  type: 'lock';
  data: {
    action: 'lock' | 'unlock';
    locked_by?: string;
  };
}

// Analytics and metrics
export interface CollaborationMetrics {
  document_id: string;
  total_users: number;
  active_users: number;
  total_operations: number;
  operations_per_minute: number;
  conflicts_resolved: number;
  comments_added: number;
  suggestions_made: number;
  average_response_time: number;
  uptime_percentage: number;
}

export interface UserActivityMetrics {
  user_id: string;
  document_id: string;
  session_duration: number;
  operations_count: number;
  characters_typed: number;
  characters_deleted: number;
  comments_added: number;
  suggestions_made: number;
  conflicts_created: number;
  last_activity: string;
}

// Configuration
export interface CollaborationConfig {
  websocket_url: string;
  auto_save_interval: number;
  presence_update_interval: number;
  conflict_resolution_strategy: ConflictResolutionStrategy;
  max_operations_buffer: number;
  operation_timeout: number;
  heartbeat_interval: number;
  reconnect_attempts: number;
  reconnect_delay: number;
  enable_analytics: boolean;
}

// Error types
export class CollaborationError extends Error {
  code: string;
  document_id?: string;
  user_id?: string;

  constructor(message: string, code: string, document_id?: string, user_id?: string) {
    super(message);
    this.name = 'CollaborationError';
    this.code = code;
    this.document_id = document_id;
    this.user_id = user_id;
  }
}

export enum CollaborationErrorCode {
  CONNECTION_FAILED = 'connection_failed',
  DOCUMENT_NOT_FOUND = 'document_not_found',
  PERMISSION_DENIED = 'permission_denied',
  OPERATION_FAILED = 'operation_failed',
  CONFLICT_RESOLUTION_FAILED = 'conflict_resolution_failed',
  SAVE_FAILED = 'save_failed',
  LOCK_FAILED = 'lock_failed',
  INVALID_OPERATION = 'invalid_operation',
  USER_NOT_FOUND = 'user_not_found',
  DOCUMENT_LOCKED = 'document_locked'
}
