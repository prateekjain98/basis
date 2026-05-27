export const DEFAULT_CHAT_MODEL = "gpt-4o-mini";

export const titleModel = {
  id: "gpt-4o-mini",
  name: "GPT-4o mini",
  provider: "openai",
  description: "Fast model for title generation",
  gatewayOrder: ["openai"],
};

export type ModelCapabilities = {
  tools: boolean;
  vision: boolean;
  reasoning: boolean;
};

export type ChatModel = {
  id: string;
  name: string;
  provider: string;
  description: string;
  gatewayOrder?: string[];
  reasoningEffort?: "none" | "minimal" | "low" | "medium" | "high";
};

export const chatModels: ChatModel[] = [
  {
    id: "gpt-4o-mini",
    name: "GPT-4o mini",
    provider: "openai",
    description: "Fast, affordable model for most tasks",
    gatewayOrder: ["openai"],
  },
  {
    id: "gpt-4o",
    name: "GPT-4o",
    provider: "openai",
    description: "Most capable multimodal model",
    gatewayOrder: ["openai"],
  },
  {
    id: "o3-mini",
    name: "o3-mini",
    provider: "openai",
    description: "Fast reasoning model",
    gatewayOrder: ["openai"],
    reasoningEffort: "medium",
  },
  {
    id: "o1",
    name: "o1",
    provider: "openai",
    description: "Advanced reasoning model",
    gatewayOrder: ["openai"],
    reasoningEffort: "medium",
  },
  {
    id: "claude-3-5-haiku-20241022",
    name: "Claude 3.5 Haiku",
    provider: "anthropic",
    description: "Fast Anthropic model",
    gatewayOrder: ["anthropic"],
  },
  {
    id: "claude-3-5-sonnet-20241022",
    name: "Claude 3.5 Sonnet",
    provider: "anthropic",
    description: "Capable Anthropic model",
    gatewayOrder: ["anthropic"],
  },
  {
    id: "claude-3-opus-20240229",
    name: "Claude 3 Opus",
    provider: "anthropic",
    description: "Most capable Anthropic model",
    gatewayOrder: ["anthropic"],
  },
  {
    id: "gemini-2.0-flash-001",
    name: "Gemini 2.0 Flash",
    provider: "google",
    description: "Fast Google model",
    gatewayOrder: ["google"],
  },
  {
    id: "gemini-2.5-pro-preview-03-25",
    name: "Gemini 2.5 Pro",
    provider: "google",
    description: "Most capable Google model",
    gatewayOrder: ["google"],
  },
  {
    id: "gemini-2.0-flash-lite-001",
    name: "Gemini 2.0 Flash Lite",
    provider: "google",
    description: "Lightweight Google model",
    gatewayOrder: ["google"],
  },
];

export async function getCapabilities(): Promise<
  Record<string, ModelCapabilities>
> {
  const results = await Promise.all(
    chatModels.map(async (model) => {
      // All our models support tools and reasoning; vision is provider-specific
      const hasVision = model.provider === "openai" || model.provider === "google";
      const hasReasoning = model.id.startsWith("o") || model.id.includes("reasoning");
      return [
        model.id,
        {
          tools: true,
          vision: hasVision,
          reasoning: hasReasoning,
        },
      ];
    })
  );

  return Object.fromEntries(results);
}

export const isDemo = process.env.IS_DEMO === "1";

type GatewayModel = {
  id: string;
  name: string;
  type?: string;
  tags?: string[];
};

export type GatewayModelWithCapabilities = ChatModel & {
  capabilities: ModelCapabilities;
};

export async function getAllGatewayModels(): Promise<
  GatewayModelWithCapabilities[]
> {
  try {
    const res = await fetch("https://ai-gateway.vercel.sh/v1/models", {
      next: { revalidate: 86_400 },
    });
    if (!res.ok) {
      return [];
    }

    const json = await res.json();
    return (json.data ?? [])
      .filter((m: GatewayModel) => m.type === "language")
      .map((m: GatewayModel) => ({
        id: m.id,
        name: m.name,
        provider: m.id.split("/")[0],
        description: "",
        capabilities: {
          tools: m.tags?.includes("tool-use") ?? false,
          vision: m.tags?.includes("vision") ?? false,
          reasoning: m.tags?.includes("reasoning") ?? false,
        },
      }));
  } catch {
    return [];
  }
}

export function getActiveModels(): ChatModel[] {
  return chatModels;
}

export const allowedModelIds = new Set(chatModels.map((m) => m.id));

export const modelsByProvider = chatModels.reduce(
  (acc, model) => {
    if (!acc[model.provider]) {
      acc[model.provider] = [];
    }
    acc[model.provider].push(model);
    return acc;
  },
  {} as Record<string, ChatModel[]>
);
