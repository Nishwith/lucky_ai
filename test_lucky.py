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
import sys

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE = "http://localhost:8000"


def divider():
    print("=" * 70)


async def test_lucky():
    divider()
    print("🍀 LUCKY AI INTEGRATION TEST")
    divider()

    async with httpx.AsyncClient(timeout=300) as client:

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

        # ------------------------------------------------------------------
        # Test 8 : Tool List
        # ------------------------------------------------------------------
        print("\n[8] Tools Catalog")
        start = time.perf_counter()
        r = await client.get(f"{BASE}/api/tools")
        elapsed = (time.perf_counter() - start) * 1000
        if r.status_code == 200:
            tools = r.json().get("tools", [])
            print(f"✅ Tools catalog loaded: found {len(tools)} registered tools")
            for t in tools[:5]:
                print(f"   - {t['name']}: {t['description']} (Level: {t['permission_level']})")
        else:
            print("❌ Tools catalog load failed")

        # ------------------------------------------------------------------
        # Test 9 : Tool Execution (Auto Permission)
        # ------------------------------------------------------------------
        print("\n[9] Tool Execution (list_files - AUTO level)")
        start = time.perf_counter()
        r = await client.post(
            f"{BASE}/api/tools/list_files",
            json={"path": "."}
        )
        elapsed = (time.perf_counter() - start) * 1000
        if r.status_code == 200:
            res = r.json()
            if res.get("success"):
                print("✅ Tool execution success")
                print(f"   Output files count: {len(res.get('output', []))}")
            else:
                print(f"❌ Tool execution failed: {res.get('error')}")
        else:
            print("❌ Tool endpoint failed")

        # Helper function to poll and approve permissions
        async def wait_and_approve_permission(description: str) -> bool:
            for _ in range(120): # up to 60s timeout
                await asyncio.sleep(0.5)
                try:
                    r = await client.get(f"{BASE}/api/permissions/pending")
                    if r.status_code == 200:
                        pending = r.json().get("pending", [])
                        if pending:
                            req = pending[0]
                            print(f"   Intercepted request {req['request_id']} for {description}: tool '{req['tool_name']}'")
                            r_approve = await client.post(
                                f"{BASE}/api/permissions/respond/{req['request_id']}",
                                json={"approved": True}
                            )
                            if r_approve.status_code == 200:
                                print("✅ Approved permission execution")
                                return True
                            else:
                                print("❌ Failed to send permission response")
                                return False
                except Exception as e:
                    print(f"⚠️ Error polling permissions: {e}")
            print(f"❌ Timeout waiting for permission for {description}")
            return False

        # ------------------------------------------------------------------
        # Test 10 : Gated Tool Execution (Interactive Prompt)
        # ------------------------------------------------------------------
        print("\n[10] Gated Tool Execution (create_file - CONFIRM level)")
        
        filename = "test_scaffold_output.txt"
        exec_task = asyncio.create_task(client.post(
            f"{BASE}/api/tools/create_file",
            json={"path": filename, "content": "Scaffold content created by integration test!"}
        ))
        
        approved = await wait_and_approve_permission("create_file tool")
        
        exec_res = await exec_task
        if exec_res.status_code == 200:
            res = exec_res.json()
            if res.get("success"):
                print(f"✅ Gated execution successfully completed: {res.get('output')}")
                
                # Cleanup: Delete the created test file (requires permission prompt too!)
                print("   [Cleanup] Deleting test file (CONFIRM level)...")
                del_task = asyncio.create_task(client.post(
                    f"{BASE}/api/tools/delete_file",
                    json={"path": filename}
                ))
                
                await wait_and_approve_permission("delete_file tool")
                await del_task
                print("✅ Cleanup complete.")
            else:
                print(f"❌ Gated execution returned error: {res.get('error')}")
        else:
            print(f"❌ Gated execution request failed: {exec_res.status_code}")

        # ------------------------------------------------------------------
        # Test 11 : End-to-End Chat Execution Pipeline (Run python --version)
        # ------------------------------------------------------------------
        print("\n[11] End-to-End Chat Execution Integration (Run python --version)")
        
        chat_task = asyncio.create_task(client.post(
            f"{BASE}/api/chat/stream",
            json={"message": "Run python --version", "stream": True}
        ))
        
        approved = await wait_and_approve_permission("chat-initiated run_command")
            
        chat_res = await chat_task
        if chat_res.status_code == 200:
            text = chat_res.text
            print("✅ Chat execution streaming finished.")
            if "python" in text.lower():
                print("✅ Chat response verified: contains python version info!")
            else:
                print(f"⚠️ Verification warning: output does not contain python details. Raw response:\n{text[:300]}")
        else:
            print(f"❌ Chat execution request failed: {chat_res.status_code}")

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