export async function GET() {
  return new Response(JSON.stringify({ user: { id: "demo", email: "demo@basis.ai" } }), {
    headers: { "Content-Type": "application/json" },
  });
}

export async function POST() {
  return new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json" },
  });
}
