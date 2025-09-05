import { NextRequest, NextResponse } from 'next/server'

interface ChatInitRequest {
  department: 'sales' | 'support'
  page_url: string
  user_agent: string
}

export async function POST(request: NextRequest) {
  try {
    const body: ChatInitRequest = await request.json()
    
    // Connect to existing LiveChatPlugin from the backend
    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    // Create new chat session using existing LiveChatPlugin
    const chatResponse = await fetch(`${managementApiUrl}/api/v1/plugins/live-chat/sessions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
      },
      body: JSON.stringify({
        department: body.department,
        page_url: body.page_url,
        user_agent: body.user_agent,
        source: 'marketing_website',
        initial_message: 'User opened chat from marketing website',
        metadata: {
          timestamp: new Date().toISOString(),
          referrer: request.headers.get('referer'),
        }
      }),
    })

    if (chatResponse.ok) {
      const chatData = await chatResponse.json()
      
      return NextResponse.json({
        success: true,
        session_id: chatData.session_id,
        status: 'connected',
        agent: {
          name: 'Sales Team',
          status: 'online',
          department: body.department
        },
        message: 'Chat session initialized successfully'
      })
    } else {
      // Fallback for when backend is unavailable
      return NextResponse.json({
        success: false,
        status: 'offline',
        message: 'Chat service temporarily unavailable'
      })
    }

  } catch (error) {
    console.error('Chat initialization error:', error)
    
    // Graceful fallback - still allow chat in demo mode
    return NextResponse.json({
      success: false,
      status: 'demo_mode',
      session_id: `demo-${Date.now()}`,
      agent: {
        name: 'Demo Agent',
        status: 'offline',
        department: 'sales'
      },
      message: 'Running in demo mode - messages will be logged for follow-up'
    })
  }
}