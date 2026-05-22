const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: Request) {
  const body = await request.json();

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
    return Response.json(
      { code: "offline:chat", message: "Backend error", cause: text },
      { status: backendRes.status }
    );
  }

  const reader = backendRes.body?.getReader();

  const stream = new ReadableStream({
    async start(controller) {
      if (!reader) {
        controller.close();
        return;
      }
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          controller.enqueue(value);
        }
        controller.close();
      } catch (error) {
        controller.error(error);
      }
    },
    cancel() {
      reader?.cancel();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Accel-Buffering": "no",
    },
  });
}
