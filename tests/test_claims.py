import unittest
from datetime import date
from app import create_app
from extensions import db
from models import User, Item, Claim

class ClaimsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

        # Seed two users
        self.poster = User(name="Poster User", email="poster@campus.edu")
        self.poster.set_password("PosterPass123!")

        self.claimant = User(name="Claimant User", email="claimant@campus.edu")
        self.claimant.set_password("ClaimantPass123!")

        db.session.add(self.poster)
        db.session.add(self.claimant)
        db.session.commit()

        # Seed a found item posted by poster
        self.found_item = Item(
            user_id=self.poster.id,
            title="Found Car Keys with Remote",
            description="Honda car key with black remote fob found on basketball court.",
            category="Keys & Keychains",
            report_type="found",
            incident_date=date.today(),
            location="Sports Complex",
            private_details="Key number embossed is 4920.",
            status="active"
        )
        db.session.add(self.found_item)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self, email, password):
        return self.client.post("/login", data={"email": email, "password": password}, follow_redirects=True)

    def test_submit_valid_claim(self):
        """Test claimant filing an ownership claim on a found item."""
        self.login("claimant@campus.edu", "ClaimantPass123!")

        resp = self.client.post(f"/item/{self.found_item.id}/claim", data={
            "message": "These are my Honda car keys! I lost them during practice and the remote has a small crack near the panic button."
        }, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"claim has been submitted", resp.data)

        claim = Claim.query.filter_by(item_id=self.found_item.id, claimant_id=self.claimant.id).first()
        self.assertIsNotNone(claim)
        self.assertEqual(claim.status, "pending")

    def test_prevent_self_claim(self):
        """Ensure users cannot submit a claim on their own reported item."""
        self.login("poster@campus.edu", "PosterPass123!")

        resp = self.client.post(f"/item/{self.found_item.id}/claim", data={
            "message": "Attempting to claim my own reported item should fail."
        }, follow_redirects=True)

        self.assertIn(b"cannot submit an ownership claim on your own listing", resp.data)
        claims_count = Claim.query.filter_by(item_id=self.found_item.id).count()
        self.assertEqual(claims_count, 0)

    def test_prevent_duplicate_pending_claims(self):
        """Ensure a claimant cannot submit multiple pending claims on the same item."""
        self.login("claimant@campus.edu", "ClaimantPass123!")

        # First claim
        self.client.post(f"/item/{self.found_item.id}/claim", data={
            "message": "First claim submission with genuine ownership explanation."
        }, follow_redirects=True)

        # Second claim attempt
        second_resp = self.client.post(f"/item/{self.found_item.id}/claim", data={
            "message": "Second duplicate claim attempt by the same student."
        }, follow_redirects=True)

        self.assertIn(b"already have an active pending claim", second_resp.data)
        claims_count = Claim.query.filter_by(item_id=self.found_item.id, claimant_id=self.claimant.id).count()
        self.assertEqual(claims_count, 1)

    def test_approve_claim_workflow(self):
        """Test poster approving a claim and marking item resolved."""
        # Create a pending claim
        claim = Claim(
            item_id=self.found_item.id,
            claimant_id=self.claimant.id,
            message="Valid ownership claim message with details.",
            status="pending"
        )
        competing_claimant = User(name="Second Claimant", email="second@campus.edu")
        competing_claimant.set_password("SecondPass123!")
        db.session.add(competing_claimant)
        db.session.flush()
        competing_claim = Claim(
            item_id=self.found_item.id,
            claimant_id=competing_claimant.id,
            message="A second valid ownership claim with details.",
            status="pending"
        )
        db.session.add(claim)
        db.session.add(competing_claim)
        db.session.commit()

        # Login as poster
        self.login("poster@campus.edu", "PosterPass123!")

        # Approve claim
        approve_resp = self.client.post(f"/claim/{claim.id}/approve", follow_redirects=True)
        self.assertEqual(approve_resp.status_code, 200)

        db.session.refresh(claim)
        db.session.refresh(self.found_item)
        self.assertEqual(claim.status, "approved")
        self.assertEqual(self.found_item.status, "pending_return")
        db.session.refresh(competing_claim)
        self.assertEqual(competing_claim.status, "rejected")

        # Resolve handover
        resolve_resp = self.client.post(f"/claim/{claim.id}/resolve", follow_redirects=True)
        self.assertEqual(resolve_resp.status_code, 200)

        db.session.refresh(claim)
        db.session.refresh(self.found_item)
        self.assertEqual(claim.status, "resolved")
        self.assertEqual(self.found_item.status, "resolved")

    def test_pending_claim_cannot_be_resolved(self):
        claim = Claim(
            item_id=self.found_item.id,
            claimant_id=self.claimant.id,
            message="Valid ownership claim message with details.",
            status="pending",
        )
        db.session.add(claim)
        db.session.commit()
        self.login("poster@campus.edu", "PosterPass123!")

        response = self.client.post(f"/claim/{claim.id}/resolve", follow_redirects=True)

        self.assertIn(b"Only an approved claim awaiting handover can be resolved", response.data)
        db.session.refresh(claim)
        db.session.refresh(self.found_item)
        self.assertEqual(claim.status, "pending")
        self.assertEqual(self.found_item.status, "active")

if __name__ == "__main__":
    unittest.main()
