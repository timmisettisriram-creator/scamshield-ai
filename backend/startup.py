"""
Startup script — initializes DB and seeds data.
Run manually: python startup.py
Or called automatically by main.py lifespan.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

async def run():
    from database import init_db
    from seed_db import seed
    print("Initializing database...")
    await init_db()
    print("Seeding scam entities...")
    await seed()
    print("Done! ScamShield AI is ready.")

if __name__ == "__main__":
    asyncio.run(run())
