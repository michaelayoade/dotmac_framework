export interface CommunicationChannel {
  id: string;
  name: string;
  type: 'email' | 'sms' | 'push' | 'websocket' | 'webhook' | 'chat' | 'whatsapp';
  status: 'active' | 'inactive' | 'error' | 'pending';
  config: Record<string, any>;
  metadata?: Record<string, any>;
  provider?: string;
  priority: number;
  rateLimit?: {
    requests: number;
    period: number; // in seconds
    remaining?: number;
  };
}

export interface CommunicationTemplate {
  id: string;
  name: string;
  channel: string;
  subject?: string;
  body: string;
  variables: string[];
  priority: 'low' | 'medium' | 'high' | 'critical';
  category: string;
  tags?: string[];
  version: number;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
  createdBy?: string;
}

export interface CommunicationMessage {
  id: string;
  templateId?: string;
  channel: string;
  channelType: CommunicationChannel['type'];
  recipient: string;
  subject?: string;
  body: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'draft' | 'pending' | 'sent' | 'delivered' | 'failed' | 'bounced' | 'cancelled';
  scheduledAt?: Date;
  sentAt?: Date;
  deliveredAt?: Date;
  readAt?: Date;
  failureReason?: string;
  metadata?: Record<string, any>;
  tenantId?: string;
  userId?: string;
  conversationId?: string;
  attachments?: MessageAttachment[];
}

export interface MessageAttachment {
  id: string;
  filename: string;
  contentType: string;
  size: number;
  url: string;
  thumbnailUrl?: string;
}

export interface CommunicationStats {
  totalSent: number;
  totalDelivered: number;
  totalFailed: number;
  totalRead: number;
  deliveryRate: number;
  failureRate: number;
  readRate: number;
  channelBreakdown: Record<
    string,
    {
      sent: number;
      delivered: number;
      failed: number;
      read: number;
    }
  >;
  recentActivity: CommunicationMessage[];
  trends: {
    period: string;
    sent: number[];
    delivered: number[];
    failed: number[];
  };
}

export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'agent' | 'bot' | 'system';
  senderId?: string;
  senderName?: string;
  senderAvatar?: string;
  timestamp: Date;
  status?: 'sending' | 'sent' | 'delivered' | 'read' | 'failed';
  type?: 'text' | 'image' | 'file' | 'system' | 'typing';
  conversationId: string;
  metadata?: Record<string, any>;
  attachments?: MessageAttachment[];
  replyTo?: string;
  isEdited?: boolean;
  editedAt?: Date;
}

export interface ChatConversation {
  id: string;
  participants: ChatParticipant[];
  title?: string;
  status: 'active' | 'closed' | 'waiting' | 'transferred';
  channel: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  tags?: string[];
  createdAt: Date;
  updatedAt: Date;
  lastMessage?: ChatMessage;
  unreadCount: number;
  metadata?: Record<string, any>;
  assignedTo?: string;
  department?: string;
}

export interface ChatParticipant {
  id: string;
  name: string;
  email?: string;
  avatar?: string;
  role: 'customer' | 'agent' | 'admin' | 'bot';
  status: 'online' | 'away' | 'busy' | 'offline';
  department?: string;
  title?: string;
  rating?: number;
  lastSeen?: Date;
}

export interface NotificationPreferences {
  userId: string;
  channels: {
    email: boolean;
    sms: boolean;
    push: boolean;
    inApp: boolean;
  };
  categories: Record<
    string,
    {
      enabled: boolean;
      channels: string[];
      priority: 'low' | 'medium' | 'high' | 'critical';
    }
  >;
  quietHours?: {
    enabled: boolean;
    start: string; // HH:mm format
    end: string; // HH:mm format
    timezone: string;
  };
  frequency?: {
    immediate: string[];
    digest: string[];
    never: string[];
  };
}

export interface CommunicationProvider {
  id: string;
  name: string;
  type: CommunicationChannel['type'];
  config: Record<string, any>;
  isActive: boolean;
  priority: number;
  rateLimit?: {
    requests: number;
    period: number;
  };
  features: string[];
  webhookUrl?: string;
}

export interface CommunicationEvent {
  id: string;
  type:
    | 'message_sent'
    | 'message_delivered'
    | 'message_failed'
    | 'message_read'
    | 'conversation_started'
    | 'conversation_ended'
    | 'agent_assigned';
  messageId?: string;
  conversationId?: string;
  timestamp: Date;
  data: Record<string, any>;
  userId?: string;
  tenantId?: string;
}

export interface BulkCommunicationJob {
  id: string;
  name: string;
  templateId: string;
  channel: string;
  recipients: string[];
  scheduledAt?: Date;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: {
    total: number;
    sent: number;
    failed: number;
    remaining: number;
  };
  createdAt: Date;
  startedAt?: Date;
  completedAt?: Date;
  createdBy?: string;
  metadata?: Record<string, any>;
}

export interface CommunicationSystemConfig {
  providers: CommunicationProvider[];
  channels: CommunicationChannel[];
  templates: CommunicationTemplate[];
  webhookEndpoint?: string;
  enableRealtime: boolean;
  enableAnalytics: boolean;
  enableCaching: boolean;
  cacheTimeout: number;
  retryAttempts: number;
  retryDelay: number;
  maxConcurrentJobs: number;
}
