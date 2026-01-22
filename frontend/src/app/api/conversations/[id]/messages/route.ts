import { NextResponse } from 'next/server';

// Conversation messages API route - not configured (enable_conversation_persistence is false)
export async function GET() {
  return NextResponse.json({ error: 'Conversation persistence is disabled' }, { status: 501 });
}