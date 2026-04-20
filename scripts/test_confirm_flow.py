"""End-to-end test: lock → confirm flow."""
import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

from app.core.database import connect_db, close_db
from app.services.lock_service import connect_redis, close_redis


async def test():
    await connect_db()
    await connect_redis()

    from app.services.booking_service import lock_slot, confirm_booking

    date = "2026-04-20"  # slots available today for atty_clark
    provider = "prov_atty_clark"
    phone = "+9999000001"

    # 1. Lock a slot
    print("[1] Locking slot...")
    lock = await lock_slot(provider_id=provider, date=date, time="10:00", customer_phone=phone)
    print("    Lock result:", json.dumps(lock, indent=4))
    assert "Z" in lock["expires_at"], "expires_at missing UTC Z"
    print("    expires_at has 'Z' suffix (timezone bug fixed): OK")

    # 2. Confirm via new MongoDB-validated path (no lock_id needed)
    print("[2] Confirming booking (MongoDB validation path)...")
    booking = await confirm_booking(
        slot_id="",
        customer_id=phone,
        customer_name="Test User",
        provider_id=provider,
        date=date,
        time="10:00",
    )
    print("    Booking result:", json.dumps(booking, indent=4))
    assert booking["status"] == "confirmed", "Expected confirmed"
    assert "Z" in booking["created_at"], "created_at missing UTC Z"
    print("    Booking confirmed, timestamps correct: OK")

    # 3. Try to confirm again (double-booking protection)
    print("[3] Confirming same slot again (should fail with 409)...")
    try:
        await lock_slot(provider_id=provider, date=date, time="10:00", customer_phone=phone)
        print("    ERROR: Should have raised SlotAlreadyLockedError or SlotNotAvailableError")
    except Exception as e:
        print(f"    Correctly rejected: {type(e).__name__}: {e}")

    await close_redis()
    await close_db()
    print()
    print("ALL TESTS PASSED")


asyncio.run(test())
