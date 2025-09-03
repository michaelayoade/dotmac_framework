'use client';
import React, { useEffect, useState } from 'react';
import { Card, Button, Input } from '@dotmac/primitives';

interface Message {
  id: string;
  from: 'customer' | 'agent';
  body: string;
  createdAt: string;
}

export function ConversationPanel({ ticketId = 'T-1001' }: { ticketId?: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const res = await fetch(`/api/customer/support/tickets/${ticketId}/messages`);
      const json = await res.json();
      setMessages(json.messages || []);
      setLoading(false);
    })();
  }, [ticketId]);

  const send = async () => {
    if (!text.trim()) return;
    const res = await fetch(`/api/customer/support/tickets/${ticketId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body: text }),
    });
    const json = await res.json();
    setMessages((prev) => [...prev, json]);
    setText('');
  };

  return (
    <Card className='p-4 mt-6' data-testid='conversation-panel'>
      <div className='font-semibold mb-3'>Conversation</div>
      {loading ? (
        <div className='text-sm text-muted-foreground'>Loading...</div>
      ) : (
        <div className='space-y-2 max-h-64 overflow-auto'>
          {messages.map((m) => (
            <div
              key={m.id}
              className={'text-sm ' + (m.from === 'agent' ? 'text-blue-700' : 'text-gray-800')}
            >
              <span className='font-medium mr-2'>{m.from === 'agent' ? 'Agent' : 'You'}</span>
              <span>{m.body}</span>
            </div>
          ))}
        </div>
      )}
      <div className='flex items-center gap-2 mt-3'>
        <Input
          value={text}
          onChange={(e: any) => setText(e.target.value)}
          placeholder='Type a message'
        />
        <Button onClick={send} data-testid='send-message'>
          Send
        </Button>
      </div>
    </Card>
  );
}
