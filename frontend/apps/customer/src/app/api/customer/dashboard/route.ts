import { NextRequest, NextResponse } from 'next/server';

// Mock customer data - replace with database in production
const mockDashboardData = {
  'user-123': {
    connectionStatus: 'active',
    monthlyUsage: {
      used: 45,
      total: 100,
      unit: 'GB'
    },
    currentBill: {
      amount: 89.99,
      currency: 'USD',
      dueDate: '2024-12-15'
    },
    supportTickets: {
      open: 0,
      recent: []
    },
    services: [
      {
        id: 'service-1',
        name: 'High-Speed Internet',
        status: 'active',
        speed: '100 Mbps'
      }
    ],
    recentActivity: [
      {
        id: 'activity-1',
        type: 'payment',
        description: 'Payment received',
        date: '2024-11-15',
        amount: 89.99
      }
    ]
  }
};

export async function GET(request: NextRequest) {
  try {
    const authToken = request.cookies.get('secure-auth-token');
    const portalType = request.cookies.get('portal-type');

    if (!authToken || portalType?.value !== 'customer') {
      return NextResponse.json(
        { success: false, error: 'Authentication required' },
        { status: 401 }
      );
    }

    // Extract user ID from token 
    const userIdMatch = authToken.value.match(/session_(.+?)_/);
    if (!userIdMatch) {
      return NextResponse.json(
        { success: false, error: 'Invalid token' },
        { status: 401 }
      );
    }

    const userId = userIdMatch[1];
    const dashboardData = mockDashboardData[userId as keyof typeof mockDashboardData];

    if (!dashboardData) {
      return NextResponse.json(
        { success: false, error: 'Customer data not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      data: dashboardData
    });

  } catch (error) {
    console.error('[Customer] Dashboard data error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}