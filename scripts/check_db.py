"""Quick DB verification script."""
import asyncio
from app.core.database import connect_db, close_db, get_db


async def main():
    await connect_db()
    db = get_db()

    for col in ["services", "providers", "slots", "bookings"]:
        count = await db[col].count_documents({})
        print(f"{col}: {count} docs")

    print("\n--- Services ---")
    async for doc in db.services.find():
        print(f"  {doc['_id']}: {doc['name']}")

    print("\n--- Providers ---")
    async for doc in db.providers.find():
        print(f"  {doc['_id']}: {doc['name']} (service: {doc['service_id']})")

    print("\n--- Sample slots (first 5) ---")
    async for doc in db.slots.find().limit(5):
        print(f"  {doc['provider_id']} | {doc['date']} | {doc['time']} | {doc['status']}")

    await close_db()
    print("\nAll OK!")


if __name__ == "__main__":
    asyncio.run(main())
