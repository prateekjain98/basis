export async function GET() {
  const headers = {
    "Cache-Control": "public, max-age=86400, s-maxage=86400",
  };

  // Stub — no AI Gateway configured. Frontend uses backend proxy.
  return Response.json(
    {
      capabilities: {},
      models: [],
    },
    { headers }
  );
}
