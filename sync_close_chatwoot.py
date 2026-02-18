#!/usr/bin/env python3
"""
One-time script: close all Chatwoot conversations that are cancelled/closed in DB
but still open/pending in Chatwoot.
"""
import asyncio
import httpx
import asyncpg

CHATWOOT_URL = "https://suppdev.clobus.uz"
CHATWOOT_TOKEN = "u1y8dnVihQDjgwEypXnWyAHz"
ACCOUNT_ID = 1
DB_URL = "postgresql://dev_admin:qwerty123@192.168.100.134:5432/cons_backend_dev"


async def get_desync_consultations():
    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch(
        "SELECT cons_id, status FROM cons.cons "
        "WHERE status IN ('cancelled', 'closed', 'resolved') "
        "AND cons_id NOT LIKE 'temp_%' "
        "AND cons_id NOT LIKE 'cl_%' "
        "AND cons_id NOT LIKE '%-%' "
        "AND length(cons_id) <= 10 "
        "ORDER BY cons_id::int"
    )
    await conn.close()
    return rows


async def get_chatwoot_open_conversations():
    open_ids = set()
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        for status in ["open", "pending"]:
            page = 1
            while True:
                resp = await client.get(
                    CHATWOOT_URL + "/api/v1/accounts/" + str(ACCOUNT_ID) + "/conversations",
                    headers={"api_access_token": CHATWOOT_TOKEN},
                    params={"status": status, "page": page},
                )
                data = resp.json().get("data", {})
                convs = data.get("payload", [])
                if not convs:
                    break
                for c in convs:
                    open_ids.add(str(c["id"]))
                page += 1
                if page > 50:
                    break
    return open_ids


async def close_conversation(client, conv_id, db_status):
    try:
        resp = await client.post(
            CHATWOOT_URL + "/api/v1/accounts/" + str(ACCOUNT_ID) + "/conversations/" + conv_id + "/toggle_status",
            headers={"api_access_token": CHATWOOT_TOKEN},
            json={"status": "resolved"},
        )
        if resp.status_code == 200:
            msg = "Заявка закрыта без консультации." if db_status == "cancelled" else "Заявка закрыта."
            await client.post(
                CHATWOOT_URL + "/api/v1/accounts/" + str(ACCOUNT_ID) + "/conversations/" + conv_id + "/messages",
                headers={"api_access_token": CHATWOOT_TOKEN},
                json={"content": msg, "message_type": "outgoing", "private": True},
            )
            return True
        else:
            print("  WARN: " + conv_id + " toggle returned " + str(resp.status_code))
            return False
    except Exception as e:
        print("  ERROR: " + conv_id + ": " + str(e))
        return False


async def main():
    print("=== Chatwoot Sync: Close desynchronized conversations ===")
    print("1. Getting cancelled/closed consultations from DB...")
    db_rows = await get_desync_consultations()
    db_closed = {str(r["cons_id"]): r["status"] for r in db_rows}
    print("   Found " + str(len(db_closed)) + " closed/cancelled consultations")

    print("2. Getting open/pending conversations from Chatwoot...")
    chatwoot_open = await get_chatwoot_open_conversations()
    print("   Found " + str(len(chatwoot_open)) + " open/pending conversations")

    desync = {cid: db_closed[cid] for cid in chatwoot_open if cid in db_closed}
    print("3. Found " + str(len(desync)) + " desynchronized conversations to close")

    if not desync:
        print("   Nothing to do!")
        return

    print("4. Closing...")
    success = 0
    failed = 0
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        for conv_id, db_status in sorted(desync.items(), key=lambda x: int(x[0])):
            result = await close_conversation(client, conv_id, db_status)
            if result:
                success += 1
                print("  OK: " + conv_id + " (" + db_status + ")")
            else:
                failed += 1
            await asyncio.sleep(0.1)

    print("=== DONE: " + str(success) + " closed, " + str(failed) + " failed ===")


asyncio.run(main())
