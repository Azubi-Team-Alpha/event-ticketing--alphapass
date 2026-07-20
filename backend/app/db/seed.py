"""
Database seed script for Ticket Hub.
Run: python -m app.db.seed  (from the backend/ directory)
"""
import bcrypt
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from sqlalchemy.orm import Session
from app.db.base import SessionLocal, Base, engine
from app.models.models import (
    Admin, Organizer, OrganizerStatus, Event, EventStatus,
    EventCategory, TicketType,
)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def seed_data():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # ── Admin ─────────────────────────────────────────────────────────────
        admin = db.query(Admin).filter(Admin.email == "admin@ticket-hub.com").first()
        if not admin:
            admin = Admin(
                email="admin@ticket-hub.com",
                full_name="Platform Admin",
                password_hash=hash_password("Password123"),
                is_super=True,
                email_verified=True,
            )
            db.add(admin)
            db.flush()
            print("✅ Admin created: admin@ticket-hub.com / Password123")

        # ── Organizer ─────────────────────────────────────────────────────────
        org = db.query(Organizer).filter(Organizer.email == "organizer@ticket-hub.com").first()
        if not org:
            org = Organizer(
                email="organizer@ticket-hub.com",
                full_name="Jane Smith",
                password_hash=hash_password("Password123"),
                business_name="TechEvents Co.",
                business_description="Premier tech event organizer.",
                phone="+1-555-0100",
                status=OrganizerStatus.active,
                email_verified=True,
            )
            db.add(org)
            db.flush()
            print("✅ Organizer created: organizer@ticket-hub.com / Password123")

        db.commit()

        # ── Event Categories ──────────────────────────────────────────────────
        categories = {
            "technology":  {"name": "Technology",  "slug": "technology",  "icon": "💻", "color": "#6366f1"},
            "music":       {"name": "Music",       "slug": "music",       "icon": "🎵", "color": "#ec4899"},
            "sports":      {"name": "Sports",      "slug": "sports",      "icon": "⚽", "color": "#10b981"},
            "arts":        {"name": "Arts",        "slug": "arts",        "icon": "🎨", "color": "#f59e0b"},
            "business":    {"name": "Business",    "slug": "business",    "icon": "💼", "color": "#3b82f6"},
            "food":        {"name": "Food & Drink","slug": "food",        "icon": "🍽", "color": "#ef4444"},
            "education":   {"name": "Education",   "slug": "education",   "icon": "📚", "color": "#8b5cf6"},
            "networking":  {"name": "Networking",  "slug": "networking",  "icon": "🤝", "color": "#06b6d4"},
        }
        cat_objs = {}
        for slug, data in categories.items():
            existing = db.query(EventCategory).filter(EventCategory.slug == slug).first()
            if not existing:
                cat = EventCategory(**data)
                db.add(cat)
                db.flush()
                cat_objs[slug] = cat
                print(f"  + Category: {data['name']}")
            else:
                cat_objs[slug] = existing
        db.commit()

        # ── Events ────────────────────────────────────────────────────────────
        if db.query(Event).count() == 0:
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            events_data: list[dict[str, Any]] = [
                {
                    "title": "Alpha Tech Summit 2026",
                    "description": "Join industry leaders for the biggest technology summit of the year. Cloud Computing, DevOps, Agentic AI, and Next-gen Security.",
                    "category_id": cat_objs["technology"].id,
                    "venue_name": "Silicon Valley Convention Center",
                    "city": "San Francisco", "country": "USA",
                    "banner_image_url": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=1200&auto=format&fit=crop&q=60",
                    "starts_at": now + timedelta(days=5, hours=9),
                    "ends_at": now + timedelta(days=5, hours=17),
                    "status": EventStatus.published,
                    "allow_transfers": True, "allow_resale": True,
                    "ticket_types": [
                        {"name": "General Admission", "price": "99.00", "quantity": 200, "purchase_limit": 5},
                        {"name": "VIP",               "price": "299.00","quantity": 50,  "purchase_limit": 2},
                        {"name": "Early Bird",        "price": "69.00", "quantity": 30,  "purchase_limit": 3,
                         "sales_end": now + timedelta(days=2)},
                    ],
                },
                {
                    "title": "Global AI & Robotics Expo",
                    "description": "Explore humanoid robots, LLMs, and autonomous systems with hands-on demos.",
                    "category_id": cat_objs["technology"].id,
                    "venue_name": "Metropolitan Center Hall A",
                    "city": "New York", "country": "USA",
                    "banner_image_url": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=1200&auto=format&fit=crop&q=60",
                    "starts_at": now + timedelta(days=12, hours=10),
                    "ends_at": now + timedelta(days=13, hours=18),
                    "status": EventStatus.published,
                    "allow_transfers": True, "allow_resale": False,
                    "ticket_types": [
                        {"name": "Standard",  "price": "150.00", "quantity": 300, "purchase_limit": 10},
                        {"name": "Corporate", "price": "500.00", "quantity": 20,  "purchase_limit": 20,
                         "benefits": ["Reserved seating", "Networking dinner", "Swag bag"]},
                    ],
                },
                {
                    "title": "Symphony Under the Stars",
                    "description": "An evening of classical masterpieces by the Royal Philharmonic Orchestra.",
                    "category_id": cat_objs["music"].id,
                    "venue_name": "Central Park Open Air Theater",
                    "city": "New York", "country": "USA",
                    "banner_image_url": "https://images.unsplash.com/photo-1465847899084-d164df4dedc6?w=1200&auto=format&fit=crop&q=60",
                    "starts_at": now + timedelta(days=3, hours=19),
                    "ends_at": now + timedelta(days=3, hours=22),
                    "status": EventStatus.published,
                    "allow_transfers": True, "allow_resale": False,
                    "ticket_types": [
                        {"name": "Lawn",     "price": "0.00",  "quantity": 500, "purchase_limit": 8},
                        {"name": "Reserved", "price": "45.00", "quantity": 200, "purchase_limit": 4},
                    ],
                },
                {
                    "title": "UX/UI Design Masterclass",
                    "description": "Learn conversion-optimized, premium interface design from top product designers.",
                    "category_id": cat_objs["education"].id,
                    "venue_name": "Design Hub Labs",
                    "city": "Accra", "country": "Ghana",
                    "is_online": True, "online_url": "https://zoom.us/j/example",
                    "banner_image_url": "https://images.unsplash.com/photo-1586717791821-3f44a563fa4c?w=1200&auto=format&fit=crop&q=60",
                    "starts_at": now + timedelta(days=20, hours=14),
                    "ends_at": now + timedelta(days=20, hours=17),
                    "status": EventStatus.published,
                    "allow_transfers": False, "allow_resale": False,
                    "ticket_types": [
                        {"name": "Student",    "price": "25.00", "quantity": 30, "purchase_limit": 1},
                        {"name": "Individual", "price": "45.50", "quantity": 50, "purchase_limit": 1},
                    ],
                },
                {
                    "title": "[Draft] Internal Team Alpha Hackathon",
                    "description": "Private hackathon for Team Alpha. Not published.",
                    "category_id": cat_objs["technology"].id,
                    "venue_name": "Team Office", "city": "Remote",
                    "starts_at": now + timedelta(days=1, hours=9),
                    "ends_at": now + timedelta(days=1, hours=17),
                    "status": EventStatus.draft,
                    "allow_transfers": False, "allow_resale": False,
                    "ticket_types": [
                        {"name": "Participant", "price": "0.00", "quantity": 20, "purchase_limit": 1},
                    ],
                },
            ]

            for ed in events_data:
                ticket_types_data = ed.pop("ticket_types", [])
                event = Event(**ed, organizer_id=org.id)
                db.add(event)
                db.flush()

                for ttd in ticket_types_data:
                    benefits = ttd.pop("benefits", None)
                    tt = TicketType(**ttd, event_id=event.id, benefits=benefits)
                    db.add(tt)

            db.commit()
            print(f"✅ Seeded {len(events_data)} events with ticket types")
        else:
            print("ℹ️  Events already seeded. Skipping.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
