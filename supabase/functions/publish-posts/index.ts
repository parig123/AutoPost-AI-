// Supabase Edge Function: publish-posts
// This function is invoked by pg_cron on a schedule.
// It calls your Vercel-hosted Flask app's /api/cron/publish endpoint,
// passing the shared CRON_SECRET so Flask can verify the request.

Deno.serve(async (_req) => {
  const vercelAppUrl = Deno.env.get("VERCEL_APP_URL");
  const cronSecret = Deno.env.get("CRON_SECRET");

  if (!vercelAppUrl || !cronSecret) {
    console.error("[publish-posts] Missing VERCEL_APP_URL or CRON_SECRET env vars.");
    return new Response(
      JSON.stringify({ error: "Server misconfiguration: missing env vars." }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }

  const endpoint = `${vercelAppUrl}/api/cron/publish`;

  try {
    console.log(`[publish-posts] Calling Flask cron endpoint: ${endpoint}`);
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // This is the shared secret Flask checks to verify it's us
        "X-Cron-Auth": cronSecret,
      },
    });

    const body = await response.json();
    console.log(`[publish-posts] Response from Flask: ${response.status}`, body);

    return new Response(JSON.stringify({ status: response.status, body }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    console.error("[publish-posts] Fetch error:", err.message);
    return new Response(
      JSON.stringify({ error: err.message }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
});
