import { NextRequest, NextResponse } from 'next/server';

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const timeRange = url.searchParams.get('timeRange') || '7d';
  return NextResponse.json({
    metrics: {
      downMbps: 487.3,
      upMbps: 493.1,
      latencyMs: 12,
      jitterMs: 2,
      lossPct: 0.001,
      uptimePct: 0.999,
    },
    signal: { strengthDbm: -55, qualityPct: 0.92 },
    trends: [
      { t: 'T-4', down: 450, up: 470 },
      { t: 'T-3', down: 470, up: 480 },
      { t: 'T-2', down: 490, up: 495 },
      { t: 'T-1', down: 485, up: 492 },
      { t: 'T-0', down: 487, up: 493 },
    ],
    incidents: [
      { id: 'INC-1001', title: 'Area maintenance', status: 'monitoring', eta: '2h' }
    ],
    timeRange,
  });
}

export async function POST(req: NextRequest) {
  // Create issue
  const body = await req.json().catch(() => ({}));
  return NextResponse.json({ id: 'INC-NEW', createdAt: new Date().toISOString(), status: 'open', ...body });
}

