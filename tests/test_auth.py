import unittest
from unittest.mock import patch
from app import create_app
from config import config
from extensions import db
from models import User

class AuthTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_hashing(self):
        """Verify that passwords are cryptographically hashed and cannot be read as plaintext."""
        u = User(name="Test User", email="test@campus.edu")
        u.set_password("MySecurePass123!")
        self.assertNotEqual(u.password_hash, "MySecurePass123!")
        self.assertTrue(u.check_password("MySecurePass123!"))
        self.assertFalse(u.check_password("WrongPassword"))

    def test_registration_success(self):
        """Test successful registration with valid inputs."""
        response = self.client.post("/register", data={
            "name": "Jane Doe",
            "email": "jane@campus.edu",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Account successfully created", response.data)
        
        user = User.query.filter_by(email="jane@campus.edu").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.name, "Jane Doe")
        self.assertEqual(user.role, "student")

    def test_registration_duplicate_email(self):
        """Test that registering with an existing email is prevented."""
        u = User(name="First User", email="duplicate@campus.edu")
        u.set_password("Password123!")
        db.session.add(u)
        db.session.commit()

        response = self.client.post("/register", data={
            "name": "Second User",
            "email": "duplicate@campus.edu",
            "password": "Password123!",
            "confirm_password": "Password123!"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"already exists", response.data)

    def test_login_and_logout(self):
        """Test login with valid and invalid credentials, and subsequent logout."""
        u = User(name="Login Tester", email="login@campus.edu")
        u.set_password("CorrectPass123!")
        db.session.add(u)
        db.session.commit()

        # Failed login: bad password
        bad_resp = self.client.post("/login", data={
            "email": "login@campus.edu",
            "password": "WrongPassword"
        }, follow_redirects=True)
        self.assertIn(b"Invalid email or password", bad_resp.data)

        # Successful login
        good_resp = self.client.post("/login", data={
            "email": "login@campus.edu",
            "password": "CorrectPass123!"
        }, follow_redirects=True)
        self.assertIn(b"Welcome back", good_resp.data)

        # Logout
        logout_resp = self.client.get("/logout", follow_redirects=True)
        self.assertIn(b"signed out", logout_resp.data)

    def test_login_rejects_external_next_url(self):
        user = User(name="Redirect Tester", email="redirect@campus.edu")
        user.set_password("CorrectPass123!")
        db.session.add(user)
        db.session.commit()

        response = self.client.post(
            "/login?next=//example.com/path",
            data={"email": "redirect@campus.edu", "password": "CorrectPass123!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard")

    def test_login_allows_safe_local_next_url(self):
        user = User(name="Redirect Tester", email="redirect@campus.edu")
        user.set_password("CorrectPass123!")
        db.session.add(user)
        db.session.commit()

        response = self.client.post(
            "/login?next=/browse%3Ftype%3Dfound",
            data={"email": "redirect@campus.edu", "password": "CorrectPass123!"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/browse?type=found")

    def test_production_requires_secret_key(self):
        with patch.object(config["production"], "SECRET_KEY", ""):
            with self.assertRaisesRegex(RuntimeError, "strong SECRET_KEY"):
                create_app("production")

if __name__ == "__main__":
    unittest.main()
