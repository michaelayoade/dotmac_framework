import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.ISP_API_URL || 'http://localhost:8001';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${API_BASE_URL}/billing/exchange/payments/multi-currency`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: request.headers.get('Authorization') || '',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to process multi-currency payment' },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const customerId = searchParams.get('customerId');
  const skip = searchParams.get('skip') || '0';
  const limit = searchParams.get('limit') || '50';

  if (!customerId) {
    return NextResponse.json({ error: 'Customer ID required' }, { status: 400 });
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/billing/exchange/customers/${customerId}/payments/multi-currency?skip=${skip}&limit=${limit}`,
      {
        headers: {
          Authorization: request.headers.get('Authorization') || '',
        },
      }
    );

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Failed to fetch multi-currency payments' }, { status: 500 });
  }
}
