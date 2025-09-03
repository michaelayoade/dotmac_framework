/**
 * @dotmac/support-system
 * Universal support and communication system for all portals
 */

// Types
export * from './types';

// Providers
export {
  SupportProvider,
  useSupport,
  useSupportTicketing,
  useSupportChat,
  useSupportKnowledgeBase,
  useSupportFileUpload,
  useSupportAnalytics,
} from './providers/SupportProvider';

// Components
export {
  UniversalTicketSystem,
  UniversalChatWidget,
  UniversalKnowledgeBase,
  UniversalFileUpload,
} from './components';

// Component prop types
export type {
  UniversalTicketSystemProps,
  UniversalChatWidgetProps,
  UniversalKnowledgeBaseProps,
  UniversalFileUploadProps,
} from './components';
