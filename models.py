from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db, login_manager

def utc_now():
    """Return the current UTC datetime without timezone offset for SQLite compatibility."""
    return datetime.now(timezone.utc)

@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return db.session.get(User, int(user_id))

class User(UserMixin, db.Model):
    """User account model for students and campus staff."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="student", nullable=False)  # 'student', 'admin'
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    # Relationships
    items = db.relationship("Item", backref="poster", lazy="dynamic", cascade="all, delete-orphan")
    claims = db.relationship("Claim", backref="claimant", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password: str):
        """Securely hash and store the user's password using scrypt or pbkdf2."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        """Check if user has administrative rights."""
        return self.role == "admin"

    @property
    def safe_display_name(self) -> str:
        """
        Return a safe privacy-preserving display name (e.g. 'John D.')
        to avoid exposing personal identity openly across campus.
        """
        parts = self.name.strip().split()
        if len(parts) > 1:
            return f"{parts[0]} {parts[-1][0]}."
        return self.name

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Item(db.Model):
    """Lost and Found item report model."""
    __tablename__ = "items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    report_type = db.Column(db.String(10), nullable=False, index=True)  # 'lost' or 'found'
    incident_date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(100), nullable=False, index=True)
    image_filename = db.Column(db.String(255), nullable=True)
    
    # Private verification notes: ONLY visible to poster & admin to verify claimant ownership!
    # Examples: serial number, unique scratches, lockscreen wallpaper, secret sticker.
    private_details = db.Column(db.Text, nullable=True)
    
    status = db.Column(db.String(20), default="active", nullable=False, index=True)
    # Status options: 'active', 'pending_return', 'resolved', 'closed'

    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    claims = db.relationship("Claim", backref="item", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def is_active(self) -> bool:
        return self.status == "active"

    @property
    def is_resolved(self) -> bool:
        return self.status == "resolved"

    @property
    def is_lost(self) -> bool:
        return self.report_type == "lost"

    @property
    def is_found(self) -> bool:
        return self.report_type == "found"

    @property
    def status_badge_class(self) -> str:
        mapping = {
            "active": "badge-active",
            "pending_return": "badge-pending",
            "resolved": "badge-resolved",
            "closed": "badge-closed",
        }
        return mapping.get(self.status, "badge-secondary")

    def __repr__(self):
        return f"<Item #{self.id} [{self.report_type.upper()}] {self.title}>"


class Claim(db.Model):
    """Ownership claim submitted by a student for a found or lost item."""
    __tablename__ = "claims"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("items.id"), nullable=False, index=True)
    claimant_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    
    # Message describing proof of ownership or circumstances
    message = db.Column(db.Text, nullable=False)
    
    # Claim status: 'pending', 'approved', 'rejected', 'resolved'
    status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    @property
    def status_badge_class(self) -> str:
        mapping = {
            "pending": "badge-pending",
            "approved": "badge-resolved",
            "rejected": "badge-closed",
            "resolved": "badge-resolved",
        }
        return mapping.get(self.status, "badge-secondary")

    def __repr__(self):
        return f"<Claim #{self.id} for Item #{self.item_id} by User #{self.claimant_id}>"
