import { NextRequest, NextResponse } from 'next/server';

const PROJECTS = [
  {
    id: 'P-001',
    name: 'Fiber Upgrade',
    status: 'inprogress',
    stage: 'Installation',
    due: '2024-12-01',
    technician: 'John Smith',
  },
];

export async function GET() {
  return NextResponse.json({ projects: PROJECTS });
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  return NextResponse.json({ id: 'P-NEW', status: 'submitted', ...body });
}
