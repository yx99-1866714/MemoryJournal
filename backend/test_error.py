import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

from app.db import SessionLocal
from app.models.journal import Journal
from sqlalchemy import select

async def f():
    async with SessionLocal() as db:
        r = await db.execute(select(Journal).where(Journal.status == "failed").order_by(Journal.created_at.desc()))
        journals = list(r.scalars())
        
        out = []
        for j in journals:
            out.append({
                "id": str(j.id),
                "status": j.status,
                "evermemos_status": j.evermemos_status
            })
        
        with open("error_log.json", "w") as f:
            json.dump(out, f, indent=2)

if __name__ == "__main__":
    asyncio.run(f())
