import unittest
from io import BytesIO
from datetime import date, timedelta
from app import create_app
from extensions import db
from models import User, Item

class ItemsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

        # Seed two distinct users
        self.user_a = User(name="User Alpha", email="alpha@campus.edu")
        self.user_a.set_password("AlphaPass123!")
        self.user_b = User(name="User Beta", email="beta@campus.edu")
        self.user_b.set_password("BetaPass123!")
        
        db.session.add(self.user_a)
        db.session.add(self.user_b)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self, email, password):
        return self.client.post("/login", data={"email": email, "password": password}, follow_redirects=True)

    def test_report_lost_item(self):
        """Test reporting a lost item by an authenticated student."""
        self.login("alpha@campus.edu", "AlphaPass123!")

        response = self.client.post("/report/lost", data={
            "title": "Dell 65W Power Adapter",
            "report_type": "lost",
            "category": "Chargers & Cables",
            "incident_date": str(date.today()),
            "location": "Central Library",
            "description": "Black Dell original USB-C laptop charger with velcro strap.",
            "private_details": "Serial number CN-0ABCD123456"
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"published successfully", response.data)

        item = Item.query.filter_by(title="Dell 65W Power Adapter").first()
        self.assertIsNotNone(item)
        self.assertEqual(item.report_type, "lost")
        self.assertEqual(item.user_id, self.user_a.id)
        self.assertEqual(item.private_details, "Serial number CN-0ABCD123456")

    def test_browse_filters_and_search(self):
        """Test filtering by category, report type, and searching by keyword."""
        # Create sample items
        it1 = Item(
            user_id=self.user_a.id,
            title="Scientific Calculator Casio",
            description="Black Casio fx-991EX calculator",
            category="Electronics & Gadgets",
            report_type="lost",
            incident_date=date.today(),
            location="Room 201",
            status="active"
        )
        it2 = Item(
            user_id=self.user_b.id,
            title="Stainless Water Bottle",
            description="Blue Milton flask found in canteen",
            category="Water Bottles & Flasks",
            report_type="found",
            incident_date=date.today(),
            location="Main Cafeteria",
            status="active"
        )
        db.session.add(it1)
        db.session.add(it2)
        db.session.commit()

        # Browse all
        resp_all = self.client.get("/browse")
        self.assertIn(b"Scientific Calculator Casio", resp_all.data)
        self.assertIn(b"Stainless Water Bottle", resp_all.data)

        # Filter lost only
        resp_lost = self.client.get("/browse?type=lost")
        self.assertIn(b"Scientific Calculator Casio", resp_lost.data)
        self.assertNotIn(b"Stainless Water Bottle", resp_lost.data)

        # Filter by keyword search
        resp_search = self.client.get("/browse?q=Milton")
        self.assertIn(b"Stainless Water Bottle", resp_search.data)
        self.assertNotIn(b"Scientific Calculator Casio", resp_search.data)

    def test_authorization_protection_on_edit_and_delete(self):
        """Ensure User Beta cannot edit or delete User Alpha's item report."""
        item = Item(
            user_id=self.user_a.id,
            title="Alpha Protected Item",
            description="Important private item description",
            category="Books & Notebooks",
            report_type="lost",
            incident_date=date.today(),
            location="Block A",
            status="active"
        )
        db.session.add(item)
        db.session.commit()

        # Login as User Beta
        self.login("beta@campus.edu", "BetaPass123!")

        # Attempt to edit item of User Alpha
        edit_resp = self.client.get(f"/item/{item.id}/edit")
        self.assertEqual(edit_resp.status_code, 403)

        # Attempt to delete item of User Alpha
        del_resp = self.client.post(f"/item/{item.id}/delete")
        self.assertEqual(del_resp.status_code, 403)

        # Verify item still exists
        item_check = db.session.get(Item, item.id)
        self.assertIsNotNone(item_check)

    def test_edit_rejects_corrupted_replacement_image_without_saving_changes(self):
        item = Item(
            user_id=self.user_a.id,
            title="Original Listing",
            description="Original item description with enough detail.",
            category="Books & Notebooks",
            report_type="lost",
            incident_date=date.today(),
            location="Block A",
            image_filename="existing-photo.jpg",
            status="active",
        )
        db.session.add(item)
        db.session.commit()
        self.login("alpha@campus.edu", "AlphaPass123!")

        response = self.client.post(
            f"/item/{item.id}/edit",
            data={
                "title": "Changed Listing",
                "report_type": "lost",
                "category": "Books & Notebooks",
                "incident_date": str(date.today()),
                "location": "Block B",
                "description": "Changed description with sufficient detail.",
                "private_details": "",
                "image": (BytesIO(b"not an image"), "fake.png"),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid or corrupted image file", response.data)
        db.session.refresh(item)
        self.assertEqual(item.title, "Original Listing")
        self.assertEqual(item.location, "Block A")
        self.assertEqual(item.image_filename, "existing-photo.jpg")

    def test_placeholder_image_validity_and_fallback(self):
        """Verify placeholder SVG is valid XML and item without photo uses placeholder gracefully."""
        import xml.etree.ElementTree as ET

        # 1. Test placeholder static file is accessible and valid XML
        resp = self.client.get("/static/images/placeholder.svg")
        self.assertEqual(resp.status_code, 200)
        # Verify it can be parsed as valid XML (no undefined entity like &bull;)
        root = ET.fromstring(resp.data)
        self.assertIsNotNone(root)

        # 2. Test item without photo renders placeholder with is-placeholder class
        item = Item(
            user_id=self.user_a.id,
            title="Item Without Photograph",
            description="Detailed description for item without photo.",
            category="Electronics & Gadgets",
            report_type="lost",
            incident_date=date.today(),
            location="Room 101",
            image_filename=None,
            status="active",
        )
        db.session.add(item)
        db.session.commit()

        detail_resp = self.client.get(f"/item/{item.id}")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertIn(b"/static/images/placeholder.svg", detail_resp.data)
        self.assertIn(b"is-placeholder", detail_resp.data)

        # 3. Test missing upload file redirects gracefully to placeholder instead of 404
        missing_resp = self.client.get("/uploads/nonexistent-image.jpg")
        self.assertEqual(missing_resp.status_code, 302)
        self.assertIn("/static/images/placeholder.svg", missing_resp.headers["Location"])

    def test_uploaded_image_redirects_to_public_supabase_storage(self):
        self.app.config.update(
            SUPABASE_URL="https://project.supabase.co",
            SUPABASE_SECRET_KEY="server-only-secret",
            SUPABASE_STORAGE_BUCKET="item-images",
        )

        response = self.client.get("/uploads/photo.png")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.headers["Location"],
            "https://project.supabase.co/storage/v1/object/public/item-images/photo.png",
        )
        self.assertNotIn("server-only-secret", response.headers["Location"])

if __name__ == "__main__":
    unittest.main()
