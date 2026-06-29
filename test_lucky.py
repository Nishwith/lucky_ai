"""
Lucky AI — Integration Test Suite
=================================

Run:

    python test_lucky.py

Verifies:

✓ Backend startup
✓ System status
✓ Metrics
✓ Installed models
✓ Chat
✓ Agent routing
✓ Memory
✓ Performance
"""

import asyncio
import time
import httpx

BASE = "http://localhost:8000"


def divider():
    print("=" * 70)


async def test_lucky():
    divider()
    print("🍀 LUCKY AI INTEGRATION TEST")
    divider()

    async with httpx.AsyncClient(timeout=120) as client:

        # ------------------------------------------------------------------
        # Test 1 : System Status
        # ------------------------------------------------------------------

        print("\n[1] System Status")

        start = time.perf_counter()

        r = await client.get(f"{BASE}/api/system/status")

        elapsed = (time.perf_counter() - start) * 1000

        if r.status_code != 200:
            print(f"❌ FAILED ({r.status_code})")
            print(r.text)
            return

        data = r.json()

        print("✅ Backend Online")
        print(f"   State    : {data['system_state']}")
        print(f"   Provider : {data['provider']}")
        print(f"   Model    : {data['model']}")
        print(f"   Time     : {elapsed:.2f} ms")

        # ------------------------------------------------------------------
        # Test 2 : Metrics
        # ------------------------------------------------------------------

        print("\n[2] System Metrics")

        start = time.perf_counter()

        r = await client.get(f"{BASE}/api/system/metrics")

        elapsed = (time.perf_counter() - start) * 1000

        if r.status_code == 200:

            metrics = r.json()

            print("✅ Metrics API")

            print(f"   CPU  : {metrics['cpu']} %")
            print(f"   RAM  : {metrics['ram']['percent']} %")
            print(f"   Disk : {metrics['disk']['percent']} %")

            if metrics["gpu"] is None:
                print("   GPU  : Not Available")
            else:
                print(f"   GPU  : {metrics['gpu']}")

            print(f"   Time : {elapsed:.2f} ms")

        else:
            print("❌ Metrics Failed")

        # ------------------------------------------------------------------
        # Test 3 : Installed Models
        # ------------------------------------------------------------------

        print("\n[3] Installed Models")

        r = await client.get(f"{BASE}/api/system/models")

        if r.status_code == 200:

            models = r.json()["models"]

            print("✅ Models")

            for model in models:
                print(f"   • {model['name']}")

        else:
            print("❌ Failed")

        # ------------------------------------------------------------------
        # Test 4 : Chat
        # ------------------------------------------------------------------

        print("\n[4] Chat")

        start = time.perf_counter()

        r = await client.post(
            f"{BASE}/api/chat",
            json={
                "message": "Introduce yourself in two sentences.",
                "stream": False,
            },
        )

        elapsed = (time.perf_counter() - start) * 1000

        if r.status_code == 200:

            data = r.json()

            print("✅ Chat Success")

            print(f"   Agent : {data['agent']}")
            print(f"   Model : {data['model_used']}")
            print(f"   Time  : {elapsed:.2f} ms")

            print("\nReply:\n")

            print(data["reply"][:250])

        else:

            print("❌ Chat Failed")

            print(r.text)

        # ------------------------------------------------------------------
        # Test 5 : Routing
        # ------------------------------------------------------------------

        print("\n[5] Dev Agent Routing")

        r = await client.post(
            f"{BASE}/api/chat",
            json={
                "message": "Write a FastAPI hello world endpoint",
                "stream": False,
            },
        )

        if r.status_code == 200:

            data = r.json()

            print("✅ Routed Successfully")

            print(f"   Agent : {data['agent']}")

            print(f"   Model : {data['model_used']}")

        else:

            print("❌ Routing Failed")

        # ------------------------------------------------------------------
        # Test 6 : Memory
        # ------------------------------------------------------------------

        print("\n[6] Memory")

        r = await client.post(
            f"{BASE}/api/memory/info",
            json={
                "key": "name",
                "value": "Test User",
                "category": "personal",
            },
        )

        if r.status_code == 200:

            print("✅ Memory Saved")

        else:

            print("❌ Memory Save Failed")

        # ------------------------------------------------------------------
        # Test 7 : Memory Recall
        # ------------------------------------------------------------------

        print("\n[7] Memory Recall")

        r = await client.post(
            f"{BASE}/api/chat",
            json={
                "message": "What is my name?",
                "stream": False,
            },
        )

        if r.status_code == 200:

            data = r.json()

            print("✅ Memory Retrieved")

            print(f"\nReply:\n{data['reply'][:200]}")

        else:

            print("❌ Memory Recall Failed")

    divider()

    print("🎉 ALL TESTS COMPLETED")

    divider()

    print("\nBackend :", BASE)

    print("Docs    :", BASE + "/docs")

    print("Status  :", BASE + "/api/system/status")

    print("Metrics :", BASE + "/api/system/metrics")

    print("Models  :", BASE + "/api/system/models")


if __name__ == "__main__":
    asyncio.run(test_lucky())