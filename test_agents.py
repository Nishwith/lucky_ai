"""
E2E Agent Services Verification
================================
Runs agent requests against live backend while auto-approving permission prompts.
Requires: uvicorn backend.main:app running on port 8000, Ollama with qwen3:8b.
"""
import asyncio
import httpx
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://127.0.0.1:8000"

async def auto_approve_permissions(client: httpx.AsyncClient, stop_event: asyncio.Event):
    """Poll pending permissions and approve them automatically."""
    while not stop_event.is_set():
        try:
            r = await client.get(f"{BASE}/api/permissions/pending")
            if r.status_code == 200:
                pending = r.json().get("pending", [])
                for p in pending:
                    rid = p.get("request_id")
                    tool = p.get("tool_name", "?")
                    print(f"   [auto-approve] Approving '{tool}' (id={rid})")
                    await client.post(
                        f"{BASE}/api/permissions/respond/{rid}",
                        json={"approved": True, "remember": False}
                    )
        except Exception:
            pass
        await asyncio.sleep(0.5)

async def call_agent(client: httpx.AsyncClient, label: str, message: str, agent: str):
    """Call an agent and return the response dict or None on failure."""
    print(f"\n[{label}] Sending to '{agent}' agent...")
    try:
        r = await client.post(
            f"{BASE}/api/chat",
            json={"message": message, "stream": False, "force_agent": agent}
        )
        if r.status_code == 200:
            data = r.json()
            print(f"  OK  Agent: {data.get('agent','?')} | Model: {data.get('model_used','?')}")
            reply = data.get("reply", "")
            print(f"  Reply: {reply[:180]}...")
            return data
        else:
            print(f"  FAIL  status={r.status_code}")
            print(f"  {r.text[:300]}")
    except httpx.ReadTimeout:
        print(f"  FAIL  Read timeout (LLM too slow for configured timeout)")
    return None

async def main():
    print("LUCKY AI — Agent Services E2E Verification")
    print("=" * 60)

    # Very generous timeout for local LLM inference (3 LLM calls per agent)
    async with httpx.AsyncClient(timeout=300.0) as client:
        # Start background permission approver
        stop = asyncio.Event()
        approver = asyncio.create_task(auto_approve_permissions(client, stop))

        try:
            # --- Test 1: Study Agent ---
            data = await call_agent(
                client, "1-Study",
                "Explain binary search in 3 sentences and save notes to study_notes.md",
                "study"
            )
            if data:
                f = os.path.join(".", "workspace", "study_notes.md")
                if os.path.exists(f):
                    with open(f, "r", encoding="utf-8") as fh:
                        print(f"  File verified: {f} ({len(fh.read())} bytes)")
                else:
                    print(f"  File not found: {f}")

            # --- Test 2: Dev Agent ---
            data = await call_agent(
                client, "2-Dev",
                "Create a file called hello.py with a single print statement that says Hello from Lucky",
                "coding"
            )
            if data:
                f = os.path.join(".", "workspace", "hello.py")
                if os.path.exists(f):
                    with open(f, "r", encoding="utf-8") as fh:
                        print(f"  File verified: {f} ({len(fh.read())} bytes)")
                else:
                    print(f"  File not found: {f}")

            # --- Test 3: PA Agent (no tool execution, just LLM response) ---
            data = await call_agent(
                client, "3-PA",
                "Give me a quick daily briefing",
                "pa"
            )

        finally:
            stop.set()
            await approver

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")

if __name__ == "__main__":
    asyncio.run(main())
