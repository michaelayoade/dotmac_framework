'use client';

import { LiveChatWidget as UniversalLiveChatWidget } from '@dotmac/communication-system';
import { useAuth } from '@dotmac/auth';

export function LiveChatWidget() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <UniversalLiveChatWidget
      userId={user.id}
      tenantId={user.tenantId}
      position='bottom-right'
      theme='light'
      enableFileUpload={true}
      enableEmoji={true}
      enableVideo={false}
      enableVoice={false}
      quickReplies={[
        'I need help with my internet',
        'Billing question',
        'Service outage',
        'Technical support',
        'Account settings',
      ]}
      placeholder='Type your message...'
      onConversationStart={(conversationId) => {
        console.log('Chat conversation started:', conversationId);
      }}
      onConversationEnd={(conversationId) => {
        console.log('Chat conversation ended:', conversationId);
      }}
      onMessageSent={(message) => {
        console.log('Message sent:', message);
      }}
    />
  );
}
