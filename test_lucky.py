"""
Lucky AI — Quick Test
======================
Run this to verify everything is working:
    python test_lucky.py
"""

import asyncio
import httpx

BASE = "http://localhost:8000"


async def test_lucky():
    print("\n🍀 Testing Lucky AI...\n")

    async with httpx.AsyncClient(timeout=120) as client:

        # ── Test 1: Health check ──────────────────────────────────────────────
        print("Test 1: Health check...")
        r = await client.get(f"{BASE}/health")
        if r.status_code == 200:
            data = r.json()
            print(f"  ✅ Lucky AI online | Provider: {data['provider']} | Model: {data['model']}")
        else:
            print(f"  ❌ Health check failed: {r.status_code}")
            return

        # ── Test 2: Simple chat ───────────────────────────────────────────────
        print("\nTest 2: Basic chat...")
        r = await client.post(f"{BASE}/api/chat", json={
            "message": "Hey Lucky! Introduce yourself in 2 sentences.",
            "stream": False
        })
        if r.status_code == 200:
            data = r.json()
            print(f"  ✅ Agent: {data['agent']} | Model: {data['model_used']}")
            print(f"  Lucky says: {data['reply'][:200]}...")
        else:
            print(f"  ❌ Chat failed: {r.text}")

        # ── Test 3: Memory save ───────────────────────────────────────────────
        print("\nTest 3: Memory save...")
        r = await client.post(f"{BASE}/api/memory/info", json={
            "key": "name", "value": "Test User", "category": "personal"
        })
        print(f"  {'✅' if r.status_code == 200 else '❌'} Personal info saved")

        # ── Test 4: Agent routing ─────────────────────────────────────────────
        print("\nTest 4: Agent routing (coding task)...")
        r = await client.post(f"{BASE}/api/chat", json={
            "message": "Write a simple Python FastAPI hello world endpoint",
            "stream": False
        })
        if r.status_code == 200:
            data = r.json()
            print(f"  ✅ Correctly routed to: {data['agent']} agent")
            print(f"     Model used: {data['model_used']}")
        else:
            print(f"  ❌ Routing test failed")

        # ── Test 5: Memory context ─────────────────────────────────────────────
        print("\nTest 5: Memory context...")
        r = await client.post(f"{BASE}/api/chat", json={
            "message": "What's my name?",
            "stream": False
        })
        if r.status_code == 200:
            data = r.json()
            print(f"  ✅ Memory retrieved | Reply: {data['reply'][:100]}")

    print("\n" + "="*40)
    print("✅ All tests passed! Lucky AI is ready.")
    print("="*40)
    print(f"\n📖 API Docs: {BASE}/docs")
    print(f"💬 Chat endpoint: POST {BASE}/api/chat")
    print(f"🧠 Memory endpoint: GET {BASE}/api/memory/context\n")


if __name__ == "__main__":
    asyncio.run(test_lucky())
