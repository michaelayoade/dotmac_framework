/**
 * Universal Support System Types
 * Comprehensive type definitions for support and communication systems
 */

// ===== CORE SUPPORT TYPES =====

export interface BaseEntity {
  id: string;
  createdAt: string;
  updatedAt: string;
  createdBy?: string;
  updatedBy?: string;
  metadata?: Record<string, unknown>;
}

// ===== SUPPORT TICKETS =====

export enum TicketStatus {
  DRAFT = 'draft',
  OPEN = 'open',
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  WAITING_CUSTOMER = 'waiting_customer',
  RESOLVED = 'resolved',
  CLOSED = 'closed',
  CANCELLED = 'cancelled',
}

export enum TicketPriority {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  URGENT = 'urgent',
  CRITICAL = 'critical',
}

export enum TicketCategory {
  TECHNICAL = 'technical',
  BILLING = 'billing',
  SALES = 'sales',
  GENERAL = 'general',
  ACCOUNT = 'account',
  SERVICE_REQUEST = 'service_request',
  COMPLAINT = 'complaint',
  FEATURE_REQUEST = 'feature_request',
}

export interface SupportTicket extends BaseEntity {
  ticketNumber: string;
  subject: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: TicketCategory;
  customerId: string;
  customerEmail: string;
  customerName: string;
  assignedTo?: string;
  assignedTeam?: string;
  tags: string[];
  dueDate?: string;
  resolvedAt?: string;
  resolution?: string;
  customerRating?: number;
  customerFeedback?: string;
  internalNotes?: string;
  escalationLevel: number;
  source: 'web' | 'email' | 'phone' | 'chat' | 'api';
  relatedTickets: string[];
  attachments: TicketAttachment[];
  watchers: string[];
  slaBreached: boolean;
  firstResponseTime?: number;
  resolutionTime?: number;
}

export interface TicketMessage extends BaseEntity {
  ticketId: string;
  content: string;
  sender: 'customer' | 'agent' | 'system';
  senderName: string;
  senderEmail?: string;
  isInternal: boolean;
  messageType: 'text' | 'html' | 'system_event';
  attachments: MessageAttachment[];
  readBy: TicketMessageRead[];
}

export interface TicketMessageRead {
  userId: string;
  readAt: string;
}

export interface TicketAttachment {
  id: string;
  filename: string;
  originalName: string;
  mimeType: string;
  size: number;
  uploadedBy: string;
  uploadedAt: string;
  url: string;
  thumbnailUrl?: string;
}

export interface MessageAttachment extends TicketAttachment {
  messageId: string;
}

// ===== CHAT SYSTEM =====

export enum ChatStatus {
  INITIALIZING = 'initializing',
  WAITING = 'waiting',
  CONNECTED = 'connected',
  ACTIVE = 'active',
  ENDED = 'ended',
  TRANSFERRED = 'transferred',
}

export enum MessageStatus {
  SENDING = 'sending',
  SENT = 'sent',
  DELIVERED = 'delivered',
  READ = 'read',
  FAILED = 'failed',
}

export enum MessageType {
  TEXT = 'text',
  IMAGE = 'image',
  FILE = 'file',
  SYSTEM = 'system',
  TYPING = 'typing',
  QUICK_REPLY = 'quick_reply',
}

export interface ChatSession extends BaseEntity {
  sessionId: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  agentId?: string;
  agentName?: string;
  status: ChatStatus;
  startedAt: string;
  endedAt?: string;
  transferredTo?: string;
  transferReason?: string;
  waitTime: number;
  responseTime?: number;
  satisfaction?: ChatSatisfaction;
  tags: string[];
  departmentId?: string;
  priority: TicketPriority;
  source: 'web' | 'mobile' | 'api';
  visitorInfo: VisitorInfo;
  conversationSummary?: string;
  relatedTicketId?: string;
}

export interface ChatMessage extends BaseEntity {
  sessionId: string;
  content: string;
  sender: 'customer' | 'agent' | 'bot' | 'system';
  senderName: string;
  senderAvatar?: string;
  messageType: MessageType;
  status: MessageStatus;
  readAt?: string;
  editedAt?: string;
  attachments: ChatAttachment[];
  quickReplies?: QuickReply[];
  metadata?: Record<string, unknown>;
}

export interface ChatAttachment {
  id: string;
  filename: string;
  originalName: string;
  mimeType: string;
  size: number;
  url: string;
  thumbnailUrl?: string;
  uploadedAt: string;
}

export interface QuickReply {
  id: string;
  text: string;
  value: string;
  metadata?: Record<string, unknown>;
}

export interface VisitorInfo {
  userAgent: string;
  ipAddress: string;
  location?: {
    country: string;
    region: string;
    city: string;
  };
  referrer?: string;
  pageUrl: string;
  sessionDuration: number;
  pagesViewed: number;
  isReturning: boolean;
  customFields?: Record<string, unknown>;
}

export interface ChatSatisfaction {
  rating: number;
  feedback?: string;
  ratedAt: string;
}

export interface AgentInfo {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  status: AgentStatus;
  title: string;
  department: string;
  rating: number;
  activeChats: number;
  maxConcurrentChats: number;
  skills: string[];
  languages: string[];
  timezone: string;
}

export enum AgentStatus {
  ONLINE = 'online',
  BUSY = 'busy',
  AWAY = 'away',
  OFFLINE = 'offline',
}

// ===== KNOWLEDGE BASE =====

export enum ArticleStatus {
  DRAFT = 'draft',
  PUBLISHED = 'published',
  ARCHIVED = 'archived',
  UNDER_REVIEW = 'under_review',
}

export enum ArticleType {
  ARTICLE = 'article',
  VIDEO = 'video',
  GUIDE = 'guide',
  FAQ = 'faq',
  TUTORIAL = 'tutorial',
}

export enum DifficultyLevel {
  BEGINNER = 'beginner',
  INTERMEDIATE = 'intermediate',
  ADVANCED = 'advanced',
}

export interface KnowledgeBaseArticle extends BaseEntity {
  title: string;
  slug: string;
  content: string;
  excerpt: string;
  status: ArticleStatus;
  type: ArticleType;
  categoryId: string;
  authorId: string;
  authorName: string;
  difficulty: DifficultyLevel;
  readTime: number;
  publishedAt?: string;
  lastReviewedAt?: string;
  reviewedBy?: string;
  tags: string[];
  views: number;
  likes: number;
  dislikes: number;
  helpfulCount: number;
  notHelpfulCount: number;
  rating: number;
  ratingCount: number;
  featuredImage?: string;
  videoUrl?: string;
  attachments: KBAttachment[];
  relatedArticles: string[];
  searchKeywords: string[];
  internalNotes?: string;
  seoTitle?: string;
  seoDescription?: string;
}

export interface KnowledgeBaseCategory extends BaseEntity {
  name: string;
  slug: string;
  description: string;
  icon?: string;
  color?: string;
  parentId?: string;
  sortOrder: number;
  isPublic: boolean;
  articlesCount: number;
  path: string[];
}

export interface KBAttachment {
  id: string;
  filename: string;
  originalName: string;
  mimeType: string;
  size: number;
  url: string;
  uploadedAt: string;
  uploadedBy: string;
}

export interface ArticleVote {
  articleId: string;
  userId: string;
  type: 'helpful' | 'not_helpful' | 'like' | 'dislike';
  createdAt: string;
}

export interface ArticleComment extends BaseEntity {
  articleId: string;
  userId: string;
  userName: string;
  userAvatar?: string;
  content: string;
  parentId?: string;
  isPublic: boolean;
  isModerated: boolean;
  moderatedBy?: string;
  moderatedAt?: string;
  likes: number;
  replies: ArticleComment[];
}

// ===== FILE UPLOAD =====

export interface FileUploadConfig {
  maxFileSize: number;
  maxFiles: number;
  acceptedFileTypes: string[];
  enableMultiple: boolean;
  enableDragDrop: boolean;
  enablePreview: boolean;
  enableProgress: boolean;
  autoUpload: boolean;
  uploadUrl?: string;
  chunkSize?: number;
  enableChunkedUpload: boolean;
  enableImageCompression: boolean;
  imageCompressionQuality?: number;
  enableVirusScan: boolean;
  customValidation?: (file: File) => string | null;
}

export interface UploadedFile {
  id: string;
  filename: string;
  originalName: string;
  size: number;
  mimeType: string;
  uploadedAt: string;
  uploadedBy: string;
  url: string;
  thumbnailUrl?: string;
  status: FileUploadStatus;
  progress: number;
  error?: string;
  metadata?: Record<string, unknown>;
}

export enum FileUploadStatus {
  PENDING = 'pending',
  UPLOADING = 'uploading',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled',
}

// ===== COMMUNICATION CENTER =====

export interface CommunicationChannel {
  id: string;
  name: string;
  type: ChannelType;
  status: ChannelStatus;
  configuration: ChannelConfiguration;
  metrics: ChannelMetrics;
  createdAt: string;
  updatedAt: string;
}

export enum ChannelType {
  EMAIL = 'email',
  CHAT = 'chat',
  PHONE = 'phone',
  SMS = 'sms',
  SOCIAL = 'social',
  WEBHOOK = 'webhook',
  API = 'api',
}

export enum ChannelStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  MAINTENANCE = 'maintenance',
  ERROR = 'error',
}

export interface ChannelConfiguration {
  enabled: boolean;
  priority: number;
  businessHours?: BusinessHours;
  autoResponse?: AutoResponse;
  routing?: RoutingRules;
  notifications?: NotificationSettings;
  customFields?: Record<string, unknown>;
}

export interface BusinessHours {
  enabled: boolean;
  timezone: string;
  schedule: DaySchedule[];
  holidays: string[];
  outOfHoursMessage?: string;
}

export interface DaySchedule {
  day: number; // 0-6, Sunday to Saturday
  enabled: boolean;
  startTime: string; // HH:mm format
  endTime: string; // HH:mm format
}

export interface AutoResponse {
  enabled: boolean;
  trigger: 'immediate' | 'after_delay' | 'no_agent_available';
  delay: number; // in seconds
  message: string;
  templates: Record<string, string>;
}

export interface RoutingRules {
  strategy: 'round_robin' | 'least_busy' | 'skill_based' | 'priority';
  skillMatching: boolean;
  maxQueueTime: number;
  fallbackAgent?: string;
  escalationRules: EscalationRule[];
}

export interface EscalationRule {
  trigger: 'time_threshold' | 'priority' | 'keyword' | 'custom';
  condition: Record<string, unknown>;
  action: 'assign_to' | 'notify' | 'change_priority';
  target: string;
}

export interface NotificationSettings {
  email: boolean;
  sms: boolean;
  push: boolean;
  webhook: boolean;
  recipients: string[];
  templates: Record<string, string>;
}

export interface ChannelMetrics {
  totalConversations: number;
  activeConversations: number;
  averageResponseTime: number;
  averageResolutionTime: number;
  satisfactionScore: number;
  messageVolume: number;
  agentUtilization: number;
  firstContactResolution: number;
}

// ===== SEARCH & FILTERING =====

export interface SearchFilters {
  query?: string;
  status?: TicketStatus[];
  priority?: TicketPriority[];
  category?: TicketCategory[];
  assignedTo?: string[];
  createdAfter?: string;
  createdBefore?: string;
  updatedAfter?: string;
  updatedBefore?: string;
  tags?: string[];
  customFields?: Record<string, unknown>;
}

export interface SearchResult<T> {
  items: T[];
  totalCount: number;
  hasMore: boolean;
  nextCursor?: string;
  facets: SearchFacet[];
  query: string;
  executionTime: number;
}

export interface SearchFacet {
  field: string;
  values: FacetValue[];
}

export interface FacetValue {
  value: string;
  count: number;
  selected: boolean;
}

// ===== API RESPONSES =====

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  warnings?: string[];
  metadata?: Record<string, unknown>;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    totalCount: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// ===== PORTAL CONFIGURATION =====

export enum PortalType {
  CUSTOMER = 'customer',
  ADMIN = 'admin',
  AGENT = 'agent',
  MANAGEMENT = 'management',
  RESELLER = 'reseller',
  TECHNICIAN = 'technician',
}

export interface SupportConfig {
  portalType: PortalType;
  features: SupportFeatures;
  ui: UIConfiguration;
  integrations: IntegrationSettings;
  permissions: PermissionSettings;
}

export interface SupportFeatures {
  ticketing: boolean;
  liveChat: boolean;
  knowledgeBase: boolean;
  fileUpload: boolean;
  videoCall: boolean;
  phoneSupport: boolean;
  socialIntegration: boolean;
  automatedResponses: boolean;
  multilingual: boolean;
  mobileSupport: boolean;
  offlineSupport: boolean;
  analytics: boolean;
  reporting: boolean;
  apiAccess: boolean;
}

export interface UIConfiguration {
  theme: 'light' | 'dark' | 'auto';
  primaryColor: string;
  logoUrl?: string;
  customCss?: string;
  language: string;
  timezone: string;
  dateFormat: string;
  timeFormat: '12h' | '24h';
  enableAnimations: boolean;
  compactMode: boolean;
}

export interface IntegrationSettings {
  enableWebhooks: boolean;
  webhookUrl?: string;
  apiKeys: Record<string, string>;
  externalSystems: ExternalSystemConfig[];
  ssoConfig?: SSOConfiguration;
}

export interface ExternalSystemConfig {
  name: string;
  type: string;
  enabled: boolean;
  configuration: Record<string, unknown>;
  lastSync?: string;
  syncStatus: 'success' | 'error' | 'pending';
}

export interface SSOConfiguration {
  enabled: boolean;
  provider: 'saml' | 'oauth' | 'oidc';
  configuration: Record<string, unknown>;
}

export interface PermissionSettings {
  allowedActions: string[];
  restrictedFeatures: string[];
  dataAccess: 'full' | 'limited' | 'own_only';
  adminAccess: boolean;
  canExport: boolean;
  canDelete: boolean;
  canModifySettings: boolean;
}

// ===== EVENTS & WEBHOOKS =====

export interface SupportEvent {
  id: string;
  type: SupportEventType;
  entityType: 'ticket' | 'chat' | 'article' | 'file';
  entityId: string;
  action: string;
  userId: string;
  userType: 'customer' | 'agent' | 'admin' | 'system';
  timestamp: string;
  data: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export enum SupportEventType {
  TICKET_CREATED = 'ticket.created',
  TICKET_UPDATED = 'ticket.updated',
  TICKET_RESOLVED = 'ticket.resolved',
  TICKET_CLOSED = 'ticket.closed',
  MESSAGE_SENT = 'message.sent',
  CHAT_STARTED = 'chat.started',
  CHAT_ENDED = 'chat.ended',
  CHAT_TRANSFERRED = 'chat.transferred',
  FILE_UPLOADED = 'file.uploaded',
  ARTICLE_VIEWED = 'article.viewed',
  ARTICLE_VOTED = 'article.voted',
}

export interface WebhookPayload {
  event: SupportEvent;
  signature: string;
  timestamp: string;
  version: string;
}

// ===== ANALYTICS & METRICS =====

export interface SupportMetrics {
  period: DateRange;
  tickets: TicketMetrics;
  chat: ChatMetrics;
  knowledgeBase: KnowledgeBaseMetrics;
  agents: AgentMetrics;
  satisfaction: SatisfactionMetrics;
}

export interface DateRange {
  startDate: string;
  endDate: string;
}

export interface TicketMetrics {
  totalTickets: number;
  newTickets: number;
  resolvedTickets: number;
  avgResolutionTime: number;
  avgFirstResponseTime: number;
  slaCompliance: number;
  escalationRate: number;
  reopenRate: number;
  byStatus: Record<TicketStatus, number>;
  byPriority: Record<TicketPriority, number>;
  byCategory: Record<TicketCategory, number>;
}

export interface ChatMetrics {
  totalSessions: number;
  avgWaitTime: number;
  avgSessionDuration: number;
  abandonmentRate: number;
  transferRate: number;
  botResolutionRate: number;
  concurrentPeak: number;
  messageVolume: number;
}

export interface KnowledgeBaseMetrics {
  totalArticles: number;
  totalViews: number;
  searchQueries: number;
  topArticles: Array<{ id: string; title: string; views: number }>;
  deflectionRate: number;
  avgRating: number;
  helpfulnessScore: number;
}

export interface AgentMetrics {
  totalAgents: number;
  activeAgents: number;
  avgHandleTime: number;
  utilization: number;
  satisfactionScore: number;
  productivity: AgentProductivity[];
}

export interface AgentProductivity {
  agentId: string;
  agentName: string;
  ticketsHandled: number;
  avgResolutionTime: number;
  satisfactionScore: number;
  utilization: number;
}

export interface SatisfactionMetrics {
  avgRating: number;
  totalResponses: number;
  distribution: Record<number, number>;
  npsScore: number;
  trendData: SatisfactionTrend[];
}

export interface SatisfactionTrend {
  date: string;
  rating: number;
  responses: number;
}

// ===== ERROR HANDLING =====

export interface SupportError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  timestamp: string;
  stack?: string;
}

export interface ValidationError {
  field: string;
  code: string;
  message: string;
  value?: unknown;
}

// ===== REAL-TIME UPDATES =====

export interface RealtimeUpdate {
  type: string;
  entityType: string;
  entityId: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface TypingIndicator {
  sessionId: string;
  userId: string;
  userName: string;
  isTyping: boolean;
  timestamp: string;
}

export interface PresenceUpdate {
  userId: string;
  status: 'online' | 'offline' | 'away' | 'busy';
  timestamp: string;
  metadata?: Record<string, unknown>;
}
