import { NextResponse } from 'next/server';

export async function POST() {
  return NextResponse.json({ uploaded: true, categorized: 'auto' });
}

