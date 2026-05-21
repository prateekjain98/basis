import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

// In-memory mapping from frontend chatId to backend sessionId
const chatToSession = new Map<string, string>();

export async function POST(request: Request) {
  const body = await request.json();
  const chatId = body.id as string | undefined;

  // Extract user message(s) from Vercel Chat SDK format
  let messages: Array<{ role: string; content: string }> = [];

  if (body.message && Array.isArray(body.message.parts)) {
    // Single new message format
    const textParts = body.message.parts
      .filter((p: any) => p.type === "text")
      .map((p: any) => p.text);
    const content = textParts.join("");
    messages = [{ role: "user", content }];
  } else if (body.messages && Array.isArray(body.messages)) {
    // Full message history format
    messages = body.messages.map((msg: any) => {
      if (msg.parts && Array.isArray(msg.parts)) {
        const text = msg.parts
          .filter((p: any) => p.type === "text")
          .map((p: any) => p.text)
          .join("");
        return { role: msg.role, content: text };
      }
      return { role: msg.role, content: msg.content || "" };
    });
  }

  // Get existing session mapping
  const sessionId = chatId ? chatToSession.get(chatId) : undefined;

  const backendBody = {
    messages,
    session_id: sessionId || null,
  };

  const backendRes = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(backendBody),
  });

  if (!backendRes.ok) {
    const text = await backendRes.text();
    return NextResponse.json(
      { error: "Backend error", detail: text },
      { status: backendRes.status }
    );
  }

  // Stream response back, capturing session ID from first chunk if new
  const reader = backendRes.body?.getReader();
  const decoder = new TextDecoder();

  let sessionIdCaptured = false;

  const stream = new ReadableStream({
    async start(controller) {
      if (!reader) {
        controller.close();
        return;
      }
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });

        // Extract session ID from first chunk if this is a new chat
        if (!sessionIdCaptured && chatId && !sessionId) {
          const match = chunk.match(/\*\*Session:\*\* `([a-z0-9]+)`/);
          if (match) {
            chatToSession.set(chatId, match[1]);
            sessionIdCaptured = true;
          }
        }

        controller.enqueue(value);
      }
      controller.close();
    },
  });

  return new NextResponse(stream, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
