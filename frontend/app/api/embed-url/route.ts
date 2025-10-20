/**
 * Next.js App Router API route for QuickSight embed URL
 * Proxies requests to the Python backend
 */

import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    const body = await request.json();
    
    const response = await fetch(`${backendUrl}/api/embed-url`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        // Forward authorization header if present
        ...(request.headers.get('authorization') && { 
          'Authorization': request.headers.get('authorization')! 
        })
      },
      body: JSON.stringify(body)
    });

    const data = await response.json();
    
    if (response.ok) {
      return NextResponse.json(data);
    } else {
      return NextResponse.json(data, { status: response.status });
    }
  } catch (error) {
    console.error('Embed URL proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to get embed URL' }, 
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    
    const response = await fetch(`${backendUrl}/api/dashboards`, {
      method: 'GET',
      headers: { 
        'Content-Type': 'application/json',
        // Forward authorization header if present
        ...(request.headers.get('authorization') && { 
          'Authorization': request.headers.get('authorization')! 
        })
      }
    });

    const data = await response.json();
    
    if (response.ok) {
      return NextResponse.json(data);
    } else {
      return NextResponse.json(data, { status: response.status });
    }
  } catch (error) {
    console.error('Dashboard listing proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to get dashboards' }, 
      { status: 500 }
    );
  }
}