import { NextRequest, NextResponse } from 'next/server';

const store: Record<string, Array<{ id: string; from: 'customer' | 'agent'; body: string; createdAt: string }>> = {
  'T-1001': [
    { id: 'M-1', from: 'agent', body: 'Hi, can you share a speed test result?', createdAt: new Date().toISOString() }
  ]
};

export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  const { id } = params;
  return NextResponse.json({ messages: store[id] || [] });
}

export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  const { id } = params;
  const body = await req.json().catch(() => ({}));
  const msg = { id: `M-${Math.floor(Math.random() * 10000)}`, from: 'customer' as const, body: body.body || '', createdAt: new Date().toISOString() };
  store[id] = [ ...(store[id] || []), msg ];
  return NextResponse.json(msg);
}

