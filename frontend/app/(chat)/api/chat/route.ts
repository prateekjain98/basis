import { NextResponse } from "next/server";
import { deleteChatById } from "@/lib/db/queries";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: Request) {
  let body: any;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { code: "bad_request", message: "Invalid JSON" },
      { status: 400 }
    );
  }

  let messages: Array<{ role: string; content: string }> = [];

  if (body.message && Array.isArray(body.message.parts)) {
    const textParts = body.message.parts
      .filter((p: any) => p.type === "text")
      .map((p: any) => p.text);
    const content = textParts.join("");
    messages = [{ role: "user", content }];
  } else if (body.messages && Array.isArray(body.messages)) {
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

  const sessionId = body.session_id as string | undefined | null;

  const model = body.model as string | undefined | null;

  const backendBody = {
    messages,
    session_id: sessionId || null,
    model: model || null,
  };

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 55000);

    const backendRes = await fetch(`${BACKEND_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(backendBody),
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (!backendRes.ok) {
      const text = await backendRes.text();
      return NextResponse.json(
        {
          code: "backend_error",
          message: "Backend error",
          cause: text.slice(0, 500),
        },
        { status: backendRes.status }
      );
    }

    if (!backendRes.body) {
      return NextResponse.json(
        { code: "backend_error", message: "Backend returned empty body" },
        { status: 502 }
      );
    }

    // Use TransformStream to ensure proper streaming through Next.js / Vercel
    const { readable, writable } = new TransformStream();
    backendRes.body.pipeTo(writable).catch((err) => {
      console.error("[API /chat] Error piping backend stream:", err);
    });

    return new NextResponse(readable, {
      headers: {
        "Content-Type": "text/plain; charset=utf-8",
        "Cache-Control": "no-store",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (err: any) {
    if (err.name === "AbortError") {
      return NextResponse.json(
        { code: "backend_timeout", message: "Backend took too long to respond. Try a shorter query." },
        { status: 504 }
      );
    }
    console.error("[API /chat] Error forwarding to backend:", err);
    return NextResponse.json(
      {
        code: "backend_unreachable",
        message: "Cannot reach backend",
        cause: err.message,
      },
      { status: 503 }
    );
  }
}

export async function DELETE(request: Request) {
  const { searchParams } = new URL(request.url);
  const id = searchParams.get("id");
  if (!id) {
    return NextResponse.json({ error: "id required" }, { status: 400 });
  }
  try {
    await deleteChatById({ id });
    return NextResponse.json({ success: true });
  } catch (err: any) {
    console.error("[API /chat] Delete error:", err);
    return NextResponse.json({ success: false, error: err.message }, { status: 500 });
  }
}
