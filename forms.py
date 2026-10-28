from datetime import date
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField,
    PasswordField,
    BooleanField,
    SubmitField,
    SelectField,
    TextAreaField,
    DateField
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError

# Standard Campus Categories
CATEGORY_CHOICES = [
    ("", "All Categories"),
    ("Student ID & Cards", "Student ID & Cards"),
    ("Electronics & Gadgets", "Electronics & Gadgets"),
    ("Books & Notebooks", "Books & Notebooks"),
    ("Bags & Backpacks", "Bags & Backpacks"),
    ("Wallets & Purses", "Wallets & Purses"),
    ("Keys & Keychains", "Keys & Keychains"),
    ("Water Bottles & Flasks", "Water Bottles & Flasks"),
    ("Chargers & Cables", "Chargers & Cables"),
    ("Clothing & Wearables", "Clothing & Wearables"),
    ("Other Belongings", "Other Belongings"),
]

ITEM_CATEGORIES = [c for c in CATEGORY_CHOICES if c[0] != ""]

# Common Campus Locations for suggestions
CAMPUS_LOCATIONS = [
    "Central Library",
    "Main Cafeteria / Canteen",
    "Computer Science Lab Block",
    "Main Auditorium",
    "Sports Complex / Ground",
    "Block A - Classrooms",
    "Block B - Science Labs",
    "Student Activity Center (SAC)",
    "Campus Parking Lot",
    "Bus Stand / Main Gate",
    "Other Campus Location",
]

class RegistrationForm(FlaskForm):
    """User registration form with strict password constraints."""
    name = StringField(
        "Full Name",
        validators=[DataRequired(message="Please enter your full name."), Length(min=2, max=100)],
        render_kw={"placeholder": "e.g., Alex Johnson"}
    )
    email = StringField(
        "Campus Email Address",
        validators=[
            DataRequired(message="Please provide a valid email address."),
            Email(message="Please enter a valid email address."),
            Length(max=120)
        ],
        render_kw={"placeholder": "e.g., student@campus.edu"}
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Password is required."),
            Length(min=8, message="Password must be at least 8 characters long.")
        ],
        render_kw={"placeholder": "Minimum 8 characters"}
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords must match.")
        ],
        render_kw={"placeholder": "Re-enter your password"}
    )
    submit = SubmitField("Create Account")


class LoginForm(FlaskForm):
    """User login form."""
    email = StringField(
        "Email Address",
        validators=[DataRequired(message="Email is required."), Email()],
        render_kw={"placeholder": "student@campus.edu"}
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Password is required.")],
        render_kw={"placeholder": "Enter your password"}
    )
    remember_me = BooleanField("Remember me on this device")
    submit = SubmitField("Sign In")


class ReportItemForm(FlaskForm):
    """Form for reporting a Lost or Found item."""
    title = StringField(
        "Item Title / Name",
        validators=[
            DataRequired(message="Please provide a descriptive title."),
            Length(min=3, max=150, message="Title must be between 3 and 150 characters.")
        ],
        render_kw={"placeholder": "e.g., Matte Black Dell Laptop Charger 65W"}
    )
    report_type = SelectField(
        "Report Type",
        choices=[("lost", "Lost Item (I lost this)"), ("found", "Found Item (I found this)")],
        validators=[DataRequired(message="Please select whether this is a lost or found item.")]
    )
    category = SelectField(
        "Category",
        choices=ITEM_CATEGORIES,
        validators=[DataRequired(message="Please select a category.")]
    )
    incident_date = DateField(
        "Date of Incident",
        validators=[DataRequired(message="Please choose the incident date.")],
        default=date.today
    )
    location = StringField(
        "Campus Location",
        validators=[
            DataRequired(message="Please specify the campus location."),
            Length(min=2, max=100)
        ],
        render_kw={"placeholder": "e.g., Central Library, 2nd Floor Reading Room"}
    )
    description = TextAreaField(
        "Public Description",
        validators=[
            DataRequired(message="Please describe the item clearly."),
            Length(min=10, max=2000, message="Description should be at least 10 characters.")
        ],
        render_kw={
            "rows": 4,
            "placeholder": "Mention color, brand, condition, and any external markings that help identify it..."
        }
    )
    image = FileField(
        "Item Photograph (Optional)",
        validators=[
            Optional(),
            FileAllowed(["jpg", "jpeg", "png", "webp"], "Only JPG, PNG, and WebP images are allowed.")
        ]
    )
    private_details = TextAreaField(
        "Confidential Verification Details (Optional)",
        validators=[Optional(), Length(max=1000)],
        render_kw={
            "rows": 3,
            "placeholder": "🔒 Private: Serial numbers, lock screen photo, secret marks inside cover... Never shown on the public listing!"
        }
    )
    submit = SubmitField("Publish Report")

    def validate_incident_date(self, field):
        """Ensure incident date is not set in the distant future."""
        if field.data and field.data > date.today():
            raise ValidationError("Incident date cannot be in the future.")


class ClaimForm(FlaskForm):
    """Claim submission form for ownership verification."""
    message = TextAreaField(
        "Claim Explanation & Proof of Ownership",
        validators=[
            DataRequired(message="Please explain why you believe this item belongs to you."),
            Length(min=15, max=1500, message="Please provide at least 15 characters of detail to help the finder verify your ownership.")
        ],
        render_kw={
            "rows": 5,
            "placeholder": "Describe unique features, what was inside, exact time lost, or details that only the true owner would know..."
        }
    )
    submit = SubmitField("Submit Ownership Claim")
