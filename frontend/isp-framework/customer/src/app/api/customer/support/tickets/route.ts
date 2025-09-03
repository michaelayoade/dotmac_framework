import { NextRequest, NextResponse } from 'next/server';

let TICKETS = [
  {
    id: 'T-1001',
    subject: 'Slow speeds',
    priority: 'medium',
    category: 'service',
    status: 'open',
    updatedAt: new Date().toISOString(),
  },
];

export async function GET() {
  return NextResponse.json({ tickets: TICKETS });
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  const id = `T-${Math.floor(Math.random() * 10000)}`;
  const ticket = { id, status: 'open', updatedAt: new Date().toISOString(), ...body };
  TICKETS = [ticket, ...TICKETS];
  return NextResponse.json(ticket);
}
