"""Test OpenAI key, AWS Polly, and voice→database connection."""
import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, r"C:\Appointmentagent")

from dotenv import load_dotenv
load_dotenv(r"C:\Appointmentagent\.env")

# ── 1. OpenAI GPT-4o ──────────────────────────────────────────────────
def test_openai():
    import openai
    key = os.getenv("OPENAI_API_KEY", "").strip().strip('"')
    print(f"\n[1] OpenAI key prefix: {key[:20]}...")
    client = openai.OpenAI(api_key=key)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Reply with exactly: GPT-4o OK"}],
            max_tokens=10,
        )
        print(f"    GPT-4o ✅  →  {resp.choices[0].message.content!r}")
        print(f"    Tokens used: {resp.usage.total_tokens}")
        return True
    except Exception as exc:
        print(f"    GPT-4o ❌  →  {exc}")
        return False


# ── 2. AWS Polly TTS ──────────────────────────────────────────────────
def test_polly():
    import boto3
    print("\n[2] AWS Polly TTS ...")
    try:
        client = boto3.client(
            "polly",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_SECRET_KEY"),
            region_name=os.getenv("AWS_REGION", "us-east-1"),
        )
        resp = client.synthesize_speech(
            Text="Hello, your appointment is confirmed.",
            OutputFormat="mp3",
            VoiceId=os.getenv("POLLY_VOICE_ID", "Joey"),
            Engine="neural",
        )
        audio_bytes = resp["AudioStream"].read()
        print(f"    Polly ✅  →  {len(audio_bytes)} bytes of audio")
        return True
    except Exception as exc:
        print(f"    Polly ❌  →  {exc}")
        return False


# ── 3. Voice → Conversation → Database (end-to-end via services) ──────
async def test_voice_db():
    print("\n[3] Voice→Conversation→Database connection ...")
    try:
        from app.core.database import connect_db, close_db
        from app.services.lock_service import connect_redis, close_redis
        from app.services.conversation_service import handle_message

        await connect_db()
        await connect_redis()
        print("    MongoDB + Redis connected ✅")

        # Simulate a voice-originated text message through the conversation engine
        resp = await handle_message(
            session_id="test-voice-db-session",
            user_message="I need to book a doctor appointment",
        )
        print(f"    Conversation reply ✅  →  {resp.reply[:80]!r}...")
        print(f"    Intent: {resp.intent}  |  Missing: {resp.missing_fields}")

        await close_redis()
        await close_db()
        print("    Connections closed cleanly ✅")
        return True
    except Exception as exc:
        import traceback
        print(f"    Voice→DB ❌  →  {exc}")
        traceback.print_exc()
        return False


# ── 4. REST API smoke test ─────────────────────────────────────────────
def test_api_endpoints():
    import urllib.request, json
    print("\n[4] REST API smoke test (backend must be running on :8000) ...")
    tests = [
        ("GET", "http://localhost:8000/health", None),
        ("POST", "http://localhost:8000/api/v1/chat",
         json.dumps({"session_id": "smoke-test", "message": "Book a doctor"}).encode()),
    ]
    ok = True
    for method, url, body in tests:
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": "application/json"} if body else {},
                method=method,
            )
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.loads(r.read())
                if "health" in url:
                    print(f"    {url} ✅  →  {data}")
                else:
                    print(f"    {url} ✅  →  reply: {str(data.get('reply',''))[:60]!r}")
        except Exception as exc:
            print(f"    {url} ❌  →  {exc}")
            ok = False
    return ok


if __name__ == "__main__":
    results = {}
    results["openai_gpt4o"] = test_openai()
    results["aws_polly"]    = test_polly()
    results["voice_db"]     = asyncio.run(test_voice_db())
    results["api_endpoints"] = test_api_endpoints()

    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    for k, v in results.items():
        status = "✅ PASS" if v else "❌ FAIL"
        print(f"  {status}  {k}")
    all_ok = all(results.values())
    print("="*50)
    sys.exit(0 if all_ok else 1)
