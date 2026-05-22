import { HttpChatTransport } from "ai";
import type { UIMessage } from "ai";

export class PlainTextChatTransport<
  UI_MESSAGE extends UIMessage = UIMessage
> extends HttpChatTransport<UI_MESSAGE> {
  processResponseStream(stream: ReadableStream<Uint8Array>) {
    const decoder = new TextDecoder("utf-8");
    return new ReadableStream({
      start(controller) {
        controller.enqueue({ type: "start" as const });
        controller.enqueue({ type: "start-step" as const });
        controller.enqueue({ type: "text-start" as const, id: "text-1" });

        const reader = stream.getReader();
        let buffer = "";

        function pump(): void {
          reader.read().then(
            ({ done, value }) => {
              if (done) {
                if (buffer) {
                  controller.enqueue({
                    type: "text-delta" as const,
                    id: "text-1",
                    delta: buffer,
                  });
                }
                controller.enqueue({ type: "text-end" as const, id: "text-1" });
                controller.enqueue({ type: "finish-step" as const });
                controller.enqueue({ type: "finish" as const });
                controller.close();
                return;
              }

              const chunk = decoder.decode(value, { stream: true });
              buffer += chunk;

              // Emit text deltas in reasonable chunks to avoid flooding
              if (buffer.length >= 1) {
                controller.enqueue({
                  type: "text-delta" as const,
                  id: "text-1",
                  delta: buffer,
                });
                buffer = "";
              }

              pump();
            },
            (err) => {
              controller.error(err);
            }
          );
        }

        pump();
      },
    });
  }
}
