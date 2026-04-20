"""
Seed script — populates MongoDB with sample services, providers, and slots.

Usage:
    python -m scripts.seed
"""

import asyncio
from datetime import datetime, timedelta
from app.core.config import get_settings
from app.core.database import connect_db, close_db, get_db
from app.services.slot_service import generate_slots_for_provider
from app.models.service import ServiceCategory


SERVICES = [
    {"_id": "svc_doctor", "name": "Doctor Consultation", "category": ServiceCategory.DOCTOR},
    {"_id": "svc_lawyer", "name": "Legal Advice", "category": ServiceCategory.LAWYER},
    {"_id": "svc_salon", "name": "Hair Salon", "category": ServiceCategory.SALON},
]

PROVIDERS = [
    # Doctors
    {
        "_id": "prov_dr_smith",
        "name": "Dr. Alice Smith",
        "service_id": "svc_doctor",
        "availability": [
            {"day": "monday", "start_time": "09:00", "end_time": "17:00", "slot_duration_minutes": 30},
            {"day": "wednesday", "start_time": "09:00", "end_time": "13:00", "slot_duration_minutes": 30},
            {"day": "friday", "start_time": "10:00", "end_time": "16:00", "slot_duration_minutes": 30},
        ],
    },
    {
        "_id": "prov_dr_jones",
        "name": "Dr. Bob Jones",
        "service_id": "svc_doctor",
        "availability": [
            {"day": "tuesday", "start_time": "08:00", "end_time": "14:00", "slot_duration_minutes": 20},
            {"day": "thursday", "start_time": "08:00", "end_time": "14:00", "slot_duration_minutes": 20},
        ],
    },
    # Lawyers
    {
        "_id": "prov_atty_clark",
        "name": "Attorney Clara Clark",
        "service_id": "svc_lawyer",
        "availability": [
            {"day": "monday", "start_time": "10:00", "end_time": "18:00", "slot_duration_minutes": 60},
            {"day": "tuesday", "start_time": "10:00", "end_time": "18:00", "slot_duration_minutes": 60},
        ],
    },
    # Salon
    {
        "_id": "prov_salon_luxe",
        "name": "Luxe Hair Studio",
        "service_id": "svc_salon",
        "availability": [
            {"day": "monday", "start_time": "09:00", "end_time": "19:00", "slot_duration_minutes": 45},
            {"day": "tuesday", "start_time": "09:00", "end_time": "19:00", "slot_duration_minutes": 45},
            {"day": "wednesday", "start_time": "09:00", "end_time": "19:00", "slot_duration_minutes": 45},
            {"day": "thursday", "start_time": "09:00", "end_time": "19:00", "slot_duration_minutes": 45},
            {"day": "friday", "start_time": "09:00", "end_time": "19:00", "slot_duration_minutes": 45},
            {"day": "saturday", "start_time": "10:00", "end_time": "16:00", "slot_duration_minutes": 45},
        ],
    },
]


async def seed():
    await connect_db()
    db = get_db()

    # Upsert services
    for svc in SERVICES:
        await db.services.update_one({"_id": svc["_id"]}, {"$set": svc}, upsert=True)
    print(f"✓ Seeded {len(SERVICES)} services")

    # Upsert providers
    for prov in PROVIDERS:
        await db.providers.update_one({"_id": prov["_id"]}, {"$set": prov}, upsert=True)
    print(f"✓ Seeded {len(PROVIDERS)} providers")

    # Generate slots for the next 7 days
    today = datetime.utcnow().date()
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    total_slots = 0

    for prov in PROVIDERS:
        for day_offset in range(7):
            target_date = today + timedelta(days=day_offset)
            target_day = day_names[target_date.weekday()]
            for avail in prov["availability"]:
                if avail["day"] == target_day:
                    count = await generate_slots_for_provider(
                        provider_id=prov["_id"],
                        date=target_date.strftime("%Y-%m-%d"),
                        start_time=avail["start_time"],
                        end_time=avail["end_time"],
                        duration_minutes=avail["slot_duration_minutes"],
                    )
                    total_slots += count

    print(f"✓ Generated {total_slots} time slots across next 7 days")
    await close_db()


if __name__ == "__main__":
    asyncio.run(seed())
