import { NextRequest, NextResponse } from 'next/server'

interface ChatMessageRequest {
  content: string
  session_id: string
  sender_info: {
    name: string
    email: string
    company?: string
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: ChatMessageRequest = await request.json()
    
    // Validate message content
    if (!body.content || !body.session_id) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      )
    }

    const managementApiUrl = process.env.MANAGEMENT_API_URL || 'http://localhost:3000'
    const serviceToken = process.env.MANAGEMENT_SERVICE_TOKEN

    // Send message to existing LiveChatPlugin
    const messageResponse = await fetch(`${managementApiUrl}/api/v1/plugins/live-chat/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${serviceToken}`,
      },
      body: JSON.stringify({
        session_id: body.session_id,
        content: body.content,
        sender_type: 'customer',
        sender_id: body.sender_info.email,
        sender_name: body.sender_info.name || 'Customer',
        metadata: {
          email: body.sender_info.email,
          company: body.sender_info.company,
          timestamp: new Date().toISOString(),
          source: 'marketing_website'
        }
      }),
    })

    if (messageResponse.ok) {
      const messageData = await messageResponse.json()
      
      // Also create a lead in the CRM if this is the first message from this customer
      if (body.sender_info.email) {
        try {
          await fetch(`${managementApiUrl}/api/v1/leads`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${serviceToken}`,
            },
            body: JSON.stringify({
              name: body.sender_info.name,
              email: body.sender_info.email,
              company: body.sender_info.company,
              source: 'live_chat',
              status: 'new',
              initial_message: body.content,
              metadata: {
                chat_session_id: body.session_id,
                first_contact: new Date().toISOString()
              }
            }),
          })
        } catch (leadError) {
          console.error('Failed to create lead:', leadError)
          // Don't fail the message if lead creation fails
        }
      }

      return NextResponse.json({
        success: true,
        message_id: messageData.id,
        timestamp: messageData.sent_at,
        status: 'delivered'
      })

    } else {
      throw new Error('Failed to send message to chat service')
    }

  } catch (error) {
    console.error('Chat message error:', error)
    
    // In demo mode or when backend is unavailable, still log the message
    console.log('Chat message (demo mode):', {
      session: body.session_id,
      from: body.sender_info.name,
      email: body.sender_info.email,
      content: body.content,
      timestamp: new Date().toISOString()
    })

    return NextResponse.json({
      success: false,
      message: 'Message received but chat service unavailable',
      demo_mode: true
    })
  }
}