import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.MANAGEMENT_API_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const customerId = searchParams.get('customerId');

  if (!customerId) {
    return NextResponse.json({ error: 'Customer ID required' }, { status: 400 });
  }

  try {
    const response = await fetch(
      `${API_BASE_URL}/v1/billing/exchange/customers/${customerId}/currencies`,
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
    return NextResponse.json({ error: 'Failed to fetch customer currencies' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { customerId, ...currencyData } = body;

    if (!customerId) {
      return NextResponse.json({ error: 'Customer ID required' }, { status: 400 });
    }

    const response = await fetch(
      `${API_BASE_URL}/v1/billing/exchange/customers/${customerId}/currencies`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: request.headers.get('Authorization') || '',
        },
        body: JSON.stringify(currencyData),
      }
    );

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: 'Failed to add customer currency' }, { status: 500 });
  }
}
