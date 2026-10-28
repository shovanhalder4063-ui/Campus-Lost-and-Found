import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from services.matching import ItemMatcher, get_item_matches, sanitize_text

class DummyItem:
    """Mock Item class for standalone algorithmic testing."""
    def __init__(self, id, title, description, category, report_type, location=None, incident_date=None, status="active"):
        self.id = id
        self.title = title
        self.description = description
        self.category = category
        self.report_type = report_type
        self.location = location
        self.incident_date = incident_date
        self.status = status

class MatchingTestCase(unittest.TestCase):
    def setUp(self):
        self.matcher = ItemMatcher(min_score=0.15, top_k=5)
        self.today = date.today()

    def test_text_sanitization(self):
        """Verify text normalization strips punctuation and extra whitespaces."""
        raw = "  Dell  Inspiron 15, Laptop! (Charger) 65W--  "
        clean = sanitize_text(raw)
        self.assertEqual(clean, "dell inspiron 15 laptop charger 65w")
        self.assertEqual(sanitize_text(None), "")

    def test_similar_items_different_wording(self):
        """Test two reports describing the same item with slight differences."""
        lost_item = DummyItem(
            id=1,
            title="Dell 65W USB-C Laptop Charger",
            description="Black Dell 65 watt type-c laptop adapter forgotten in reading hall.",
            category="Chargers & Cables",
            report_type="lost",
            location="Central Library",
            incident_date=self.today
        )

        found_item = DummyItem(
            id=2,
            title="Found Dell 65W Type-C Power Adapter",
            description="Found a genuine Dell laptop power brick with cable plugged into wall socket.",
            category="Chargers & Cables",
            report_type="found",
            location="Central Library 2nd Floor",
            incident_date=self.today
        )

        matches = self.matcher.find_matches(lost_item, [found_item])
        self.assertEqual(len(matches), 1)
        match = matches[0]
        self.assertEqual(match["item"].id, 2)
        self.assertGreater(match["score"], 0.40)
        self.assertTrue(any("category" in r.lower() for r in match["reasons"]))
        self.assertTrue(any("location" in r.lower() for r in match["reasons"]))

    def test_completely_unrelated_items(self):
        """Test two totally unrelated items (e.g. Charger vs Water Bottle)."""
        lost_item = DummyItem(
            id=1,
            title="Dell Laptop Charger",
            description="Black electronic cable adapter",
            category="Chargers & Cables",
            report_type="lost",
            location="Library",
            incident_date=self.today
        )

        found_item = DummyItem(
            id=2,
            title="Pink Hydro Flask Water Bottle",
            description="Stainless steel vacuum insulated drink container with sports cap",
            category="Water Bottles & Flasks",
            report_type="found",
            location="Basketball Court",
            incident_date=self.today - timedelta(days=20)
        )

        matches = self.matcher.find_matches(lost_item, [found_item])
        # Unrelated item should produce zero matches exceeding threshold
        self.assertEqual(len(matches), 0)

    def test_same_type_exclusion(self):
        """Ensure a lost item is NEVER matched against another lost item."""
        lost_item_1 = DummyItem(
            id=1,
            title="Student ID Card",
            description="Card lost in canteen",
            category="Student ID & Cards",
            report_type="lost",
            location="Canteen",
            incident_date=self.today
        )

        lost_item_2 = DummyItem(
            id=2,
            title="Student ID Card",
            description="Card lost in canteen",
            category="Student ID & Cards",
            report_type="lost",
            location="Canteen",
            incident_date=self.today
        )

        matches = self.matcher.find_matches(lost_item_1, [lost_item_2])
        self.assertEqual(len(matches), 0)

    def test_self_matching_exclusion(self):
        """Ensure an item is never compared against itself."""
        item = DummyItem(
            id=1,
            title="Sony Wireless Headphones",
            description="Black over ear headphones",
            category="Electronics & Gadgets",
            report_type="lost",
            location="Lab",
            incident_date=self.today
        )

        matches = self.matcher.find_matches(item, [item])
        self.assertEqual(len(matches), 0)

    def test_resolved_status_exclusion(self):
        """Resolved reports must not appear as match candidates."""
        target = DummyItem(
            id=1,
            title="Casio Calculator",
            description="fx-991EX scientific calculator",
            category="Electronics & Gadgets",
            report_type="lost",
            location="Room 101",
            incident_date=self.today
        )

        resolved_found = DummyItem(
            id=2,
            title="Casio Calculator",
            description="fx-991EX scientific calculator",
            category="Electronics & Gadgets",
            report_type="found",
            location="Room 101",
            incident_date=self.today,
            status="resolved"  # Already reunited!
        )

        matches = self.matcher.find_matches(target, [resolved_found])
        self.assertEqual(len(matches), 0)

    def test_missing_and_empty_attributes_graceful_handling(self):
        """Verify handling of items with missing locations, empty descriptions, or None dates."""
        target = DummyItem(
            id=1,
            title="Wallet",
            description="",  # empty description
            category="Wallets & Purses",
            report_type="lost",
            location=None,
            incident_date=None
        )

        candidate = DummyItem(
            id=2,
            title="Brown Leather Wallet",
            description="Found empty leather wallet",
            category="Wallets & Purses",
            report_type="found",
            location="Parking Lot",
            incident_date=None
        )

        # Should not raise exception
        matches = self.matcher.find_matches(target, [candidate])
        self.assertIsInstance(matches, list)

    def test_empty_candidates_database(self):
        """Empty candidate list returns empty result safely."""
        target = DummyItem(
            id=1,
            title="Keys",
            description="Keychain with two brass keys",
            category="Keys & Keychains",
            report_type="lost"
        )
        matches = self.matcher.find_matches(target, [])
        self.assertEqual(matches, [])

if __name__ == "__main__":
    unittest.main()
