import { NextRequest, NextResponse } from 'next/server';

const FILES = [
  {
    id: 'F-001',
    name: 'Invoice-Feb.pdf',
    type: 'pdf',
    size: 234567,
    owner: 'me',
    lastAccessed: '2024-08-01',
    category: 'billing',
    shared: false,
  },
  {
    id: 'F-002',
    name: 'SpeedTest.png',
    type: 'image',
    size: 123456,
    owner: 'me',
    lastAccessed: '2024-08-15',
    category: 'diagnostic',
    shared: true,
  },
];

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const type = url.searchParams.get('type');
  const owner = url.searchParams.get('owner');
  let files = FILES;
  if (type) files = files.filter((f) => f.type === type);
  if (owner) files = files.filter((f) => f.owner === owner);
  return NextResponse.json({
    files,
    usage: { total: 10 * 1024 * 1024 * 1024, used: 512 * 1024 * 1024 },
  });
}

export async function POST() {
  return NextResponse.json({ success: true });
}
