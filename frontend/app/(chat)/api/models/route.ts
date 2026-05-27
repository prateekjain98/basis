import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET() {
  const headers = {
    "Cache-Control": "public, max-age=60, s-maxage=60",
  };

  try {
    const res = await fetch(`${BACKEND_URL}/models`, {
      next: { revalidate: 60 },
    });

    if (!res.ok) {
      return NextResponse.json(
        {
          capabilities: {},
          models: [],
          available_model_ids: [],
          default_model: "gpt-4o-mini",
        },
        { headers }
      );
    }

    const backendData = await res.json();

    return NextResponse.json(
      {
        capabilities: {},
        models: [],
        available_model_ids: backendData.available_models ?? [],
        default_model: backendData.default_model ?? "gpt-4o-mini",
        providers: backendData.providers ?? {},
      },
      { headers }
    );
  } catch {
    return NextResponse.json(
      {
        capabilities: {},
        models: [],
        available_model_ids: [],
        default_model: "gpt-4o-mini",
      },
      { headers }
    );
  }
}
