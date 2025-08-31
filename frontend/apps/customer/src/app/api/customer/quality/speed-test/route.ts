import { NextResponse } from 'next/server';

export async function POST() {
  // Return mock speed test results
  return NextResponse.json({
    downMbps: 488.5,
    upMbps: 494.2,
    latencyMs: 11,
    jitterMs: 2,
    lossPct: 0.001,
    durationSec: Number(process.env.NEXT_PUBLIC_SPEED_TEST_SECONDS || 10)
  });
}

