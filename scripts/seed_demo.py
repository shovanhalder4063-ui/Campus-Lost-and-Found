"""
Demo Data Seeding Script for Campus Lost & Found Portal.

Creates realistic sample users and campus item reports (Lost & Found)
with corresponding confidential verification notes, potential matches,
and sample claims for local demonstration and viva evaluation.

Usage:
    python scripts/seed_demo.py
"""

import sys
import os
from datetime import date, timedelta
from pathlib import Path

# Add project root to sys.path so models and app can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from extensions import db
from models import User, Item, Claim


def seed_database():
    app = create_app("development")

    with app.app_context():
        # Check if demo users already exist
        existing = User.query.filter_by(email="arjun.sharma@campus.edu").first()
        if existing:
            print("Demo data appears to already exist in database. Skipping duplicate seed.")
            return

        print("Seeding sample campus users...")
        users = [
            User(
                name="Arjun Sharma",
                email="arjun.sharma@campus.edu",
                role="student"
            ),
            User(
                name="Priya Patel",
                email="priya.patel@campus.edu",
                role="student"
            ),
            User(
                name="Rohan Verma",
                email="rohan.verma@campus.edu",
                role="student"
            ),
            User(
                name="Campus Admin Moderator",
                email="admin@campus.edu",
                role="admin"
            ),
        ]

        # Set default sample password 'StudentPass123!' for all demo accounts
        for u in users:
            u.set_password("StudentPass123!")
            db.session.add(u)

        db.session.commit()
        print(f"Created {len(users)} demo users (Password: StudentPass123!)")

        u_arjun = User.query.filter_by(email="arjun.sharma@campus.edu").first()
        u_priya = User.query.filter_by(email="priya.patel@campus.edu").first()
        u_rohan = User.query.filter_by(email="rohan.verma@campus.edu").first()

        today = date.today()

        print("Seeding realistic campus items...")
        items = [
            # Item 1: Lost Dell Charger (Reported by Arjun)
            Item(
                user_id=u_arjun.id,
                title="Dell 65W USB-C Laptop Charger",
                description="Original black Dell 65W type-C power adapter with a velcro cable wrap. Misplaced during the afternoon study session.",
                category="Chargers & Cables",
                report_type="lost",
                incident_date=today - timedelta(days=2),
                location="Central Library 2nd Floor Reading Room",
                private_details="Small white scratch mark on the Dell logo and red rubber band around the plug.",
                status="active"
            ),
            # Item 2: Found Dell Charger (Reported by Priya) -> EXCELLENT AI MATCH with Item 1!
            Item(
                user_id=u_priya.id,
                title="Found Dell 65W Type-C Laptop Power Adapter",
                description="Black Dell 65-watt USB-C charger left plugged into desk socket #14. Currently kept safely with the library front desk.",
                category="Chargers & Cables",
                report_type="found",
                incident_date=today - timedelta(days=2),
                location="Central Library 2nd Floor",
                private_details="Red rubber band attached to cord; white scratch on side of adapter body.",
                status="active"
            ),
            # Item 3: Lost Student ID Card (Reported by Rohan)
            Item(
                user_id=u_rohan.id,
                title="Student Identity Card - B.Tech CSE",
                description="Campus RFID smart ID card in a clear plastic protective lanyard sleeve. Lost between the cafeteria and Block B.",
                category="Student ID & Cards",
                report_type="lost",
                incident_date=today - timedelta(days=1),
                location="Main Cafeteria / Canteen",
                private_details="Roll Number ending with ...4082; barcode sticker slightly peeled on back corner.",
                status="active"
            ),
            # Item 4: Found Student ID Card (Reported by Arjun) -> EXCELLENT AI MATCH with Item 3!
            Item(
                user_id=u_arjun.id,
                title="Found Student ID Card - Computer Science",
                description="Found an official university student identity card near the south exit benches of the canteen.",
                category="Student ID & Cards",
                report_type="found",
                incident_date=today - timedelta(days=1),
                location="Main Cafeteria Benches",
                private_details="Name starts with R; plastic lanyard holder with university blue ribbon.",
                status="active"
            ),
            # Item 5: Lost Scientific Calculator (Reported by Priya)
            Item(
                user_id=u_priya.id,
                title="Casio fx-991EX ClassWiz Scientific Calculator",
                description="Black casing with carbon-texture faceplate. Left in Math exam room after calculus test.",
                category="Electronics & Gadgets",
                report_type="lost",
                incident_date=today - timedelta(days=4),
                location="Block A - Room 204",
                private_details="Priya initials engraved faintly on the inside of the sliding protective cover.",
                status="active"
            ),
            # Item 6: Found Scientific Calculator (Reported by Rohan) -> EXCELLENT AI MATCH with Item 5!
            Item(
                user_id=u_rohan.id,
                title="Found Casio Scientific Calculator ClassWiz",
                description="Black and white scientific calculator discovered on the 3rd row desk in Block A lecture hall.",
                category="Electronics & Gadgets",
                report_type="found",
                incident_date=today - timedelta(days=3),
                location="Block A - Classrooms",
                private_details="Handwritten initials 'PP' inside the sliding cover.",
                status="active"
            ),
            # Item 7: Lost Navy Blue Hydro Flask Water Bottle (Reported by Arjun)
            Item(
                user_id=u_arjun.id,
                title="Navy Blue Insulated Stainless Steel Water Bottle 750ml",
                description="Matte finish navy blue water bottle with black flex sip lid. Left on the bleachers during basketball practice.",
                category="Water Bottles & Flasks",
                report_type="lost",
                incident_date=today - timedelta(days=5),
                location="Sports Complex / Ground",
                private_details="Small dent at the bottom rim and a sticker of NASA on the side.",
                status="active"
            ),
            # Item 8: Reunited Item (Demonstrating resolved status & statistics)
            Item(
                user_id=u_priya.id,
                title="Sony WH-1000XM4 Wireless Noise Canceling Headphones",
                description="Black over-ear headphones in grey zippered hardshell carry case.",
                category="Electronics & Gadgets",
                report_type="found",
                incident_date=today - timedelta(days=10),
                location="Computer Science Lab Block",
                private_details="Braided auxiliary cable stored in the zipper pouch inside.",
                status="resolved"
            ),
        ]

        for itm in items:
            db.session.add(itm)

        db.session.commit()
        print(f"Created {len(items)} realistic demo items with corresponding AI match pairs.")

        # Seed sample claim
        found_charger = Item.query.filter_by(title="Found Dell 65W Type-C Laptop Power Adapter").first()
        if found_charger:
            sample_claim = Claim(
                item_id=found_charger.id,
                claimant_id=u_arjun.id,
                message="Hi Priya, I believe this is my Dell laptop charger. I was studying at desk 14 on Tuesday afternoon and forgot it plugged into the wall. It has a red rubber band wrapped around the cable and a tiny scratch on the Dell logo.",
                status="pending"
            )
            db.session.add(sample_claim)
            db.session.commit()
            print("Created 1 pending sample claim for testing.")

        print("\nDemo data seeding completed successfully!")
        print("Demo Accounts:")
        print("  - Student 1: arjun.sharma@campus.edu  / StudentPass123!")
        print("  - Student 2: priya.patel@campus.edu   / StudentPass123!")
        print("  - Student 3: rohan.verma@campus.edu   / StudentPass123!")
        print("  - Admin:     admin@campus.edu         / StudentPass123!")


if __name__ == "__main__":
    seed_database()
