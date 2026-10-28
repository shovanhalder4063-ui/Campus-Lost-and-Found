# Campus Lost & Found Portal 🎓🔍

> An AI-assisted web platform developed for college campuses to help students report lost belongings, log found items, discover automated potential matches via local text similarity, and securely coordinate handovers.

---

## 🌟 Key Features

1. **Public Homepage & Real Campus Statistics**:
   - Live dashboard metrics: Total Reports, Items Reunited, Active Lost, and Active Found items calculated dynamically from SQLite database queries.
   - Quick category shortcuts and dynamic keyword search across the entire campus.
   - 3-step transparent explanation: *Report &rarr; AI Match &rarr; Reunite*.

2. **Smart Browse & Multivariable Filtering**:
   - Search across titles, descriptions, and campus locations.
   - Real-time filters for Report Type (Lost / Found), Category, and Campus Location.
   - Sorting options (Newest first, Oldest first) with clean pagination.

3. **Student Privacy & Confidential Vault**:
   - Public listings protect student privacy by hiding direct phone numbers and emails.
   - **Confidential Verification Details**: When creating a report, users can store secret marks (such as serial numbers, engraved initials, or lockscreen wallpapers) in a private vault that is **never** displayed on the public website. Only the reporter and campus moderators can view it to verify genuine claimant ownership.

4. **Transparent AI-Assisted Matching Engine**:
   - Built locally using `scikit-learn` (`TfidfVectorizer` and `cosine_similarity`).
   - Requires **no external API keys**, no paid subscriptions, and no internet connection during matching.
   - Computes text similarity and combines it with contextual relevance bonuses (Category match $+15\%$, Location area overlap $+8-12\%$, Date proximity within 3 days $+5\%$).
   - Honest and explainable: clearly marked as **"Potential Match"** (never a guaranteed probability) with transparent reason chips (e.g., *"Strong description similarity (43%)"*, *"Exact category match"*, *"Reported on same date"*).

5. **Ownership Claim & Verification Workflow**:
   - Students can file ownership claims with detailed proof explanations.
   - Posters can review incoming claims in their dashboard: **Approve**, **Reject**, or confirm physical handover and mark the item **Reunited / Resolved**.
   - Built-in security: prevents students from claiming their own items and prevents duplicate pending claims.

6. **Responsive, SaaS-Grade User Interface**:
   - Warm off-white background (`#FBFBFC`), deep teal primary accent (`#0F766E`), and dark navy typography.
   - Consistent Lucide icon set and custom SVG image fallbacks.
   - Fully responsive layout across mobile, tablet, and desktop screens.

---

## 📁 Project Architecture & File Directory

```
d:\Lost&found\
├── app.py                     # Flask application factory, routes, and CLI commands
├── config.py                  # Configuration settings (Development, Testing, Production)
├── extensions.py              # Flask extensions (SQLAlchemy, LoginManager, CSRFProtect)
├── models.py                  # Database models: User, Item, Claim with password hashing
├── forms.py                   # Flask-WTF forms with server-side validation
├── services/
│   ├── __init__.py
│   └── matching.py            # Local AI text matching engine (TF-IDF + Cosine Similarity)
├── migrations/                # Versioned database schema changes (Flask-Migrate)
├── templates/
│   ├── base.html              # Base layout with navbar, alerts, Lucide icons, and footer
│   ├── index.html             # Homepage with hero, real stats, and recent items
│   ├── browse.html            # Browse page with search, filters, and pagination
│   ├── item_detail.html       # Full item view, private vault, claims & AI matches
│   ├── report_item.html       # Report Lost / Found item form with photo preview
│   ├── edit_item.html         # Edit existing report details
│   ├── dashboard.html         # User dashboard (My Lost, My Found, Claims, AI Matches)
│   ├── matches.html           # Dedicated AI Matching Hub & Explorer
│   ├── login.html             # Secure student sign-in
│   ├── register.html          # New account registration
│   └── errors/
│       ├── 404.html           # 404 Not Found error page
│       └── 500.html           # 500 Server Error page
├── static/
│   ├── css/
│   │   └── style.css          # Design system, CSS variables, cards, and responsive rules
│   ├── js/
│   │   └── main.js            # Vanilla JS: tabs, mobile menu, image preview, alerts
│   └── images/
│       └── placeholder.svg    # Clean SVG fallback placeholder for items without photos
├── uploads/                   # Local directory for user-uploaded photographs
├── tests/
│   ├── __init__.py
│   ├── test_auth.py           # Unit tests for registration, login, logout, password hashing
│   ├── test_items.py          # Unit tests for item creation, search, filters, authorization
│   ├── test_claims.py         # Unit tests for claim submission, duplicate prevention, approval
│   └── test_matching.py       # Algorithmic tests for TF-IDF, edge cases, contextual bonuses
├── scripts/
│   └── seed_demo.py           # Script to populate database with realistic campus test data
├── requirements.txt           # Minimal, documented Python dependencies
├── .env.example               # Example environment variable file
├── .gitignore                 # Files excluded from git tracking
├── README.md                  # This beginner-friendly setup guide
└── VIVA_NOTES.md              # Viva exam preparation notes and 15+ Q&As
```

---

## 🛠️ Windows Step-by-Step Setup Guide

Follow these exact steps to run the application on your Windows computer.

### Step 1: Open the Project Directory
1. Press `Windows Key + X` and select **Terminal** or **Windows PowerShell**.
2. Navigate to the project folder:
   ```powershell
   cd "d:\Lost&found"
   ```

### Step 2: Create a Virtual Environment
A virtual environment keeps your project packages isolated from the rest of your computer:
```powershell
python -m venv venv
```
*(If you are using Anaconda or another Python distribution, specify your Python path: e.g., `& "D:\Anaconda3\python.exe" -m venv venv`)*

### Step 3: Activate the Virtual Environment
If PowerShell displays a script execution policy error, enable local scripts first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
Then activate the environment:
```powershell
.\venv\Scripts\Activate.ps1
```
*(Once activated, you will see `(venv)` appear at the beginning of your command prompt line).*

### Step 4: Install Dependencies
Install all required libraries from `requirements.txt`:
```powershell
pip install -r requirements.txt
```

### Step 5: Create or update the database schema
Apply the project migrations to create a fresh database or update an existing migrated database:
```powershell
flask --app app db upgrade
```

For an existing database created before migrations were added, **back it up first**. If its schema matches the current models, mark the initial migration as already applied once:
```powershell
flask --app app db stamp head
```
Then use `flask --app app db upgrade` for future schema updates. Do not stamp a database that has not been backed up or whose schema differs from the current models.

### Step 6: Seed the Database with Sample Campus Data
After applying migrations, run the seeding script to insert realistic campus items (Dell chargers, Student IDs, scientific calculators, water bottles):
```powershell
python scripts/seed_demo.py
```

This creates four ready-to-use demo accounts:
| Role | Email | Password |
|---|---|---|
| Student 1 | `arjun.sharma@campus.edu` | `StudentPass123!` |
| Student 2 | `priya.patel@campus.edu` | `StudentPass123!` |
| Student 3 | `rohan.verma@campus.edu` | `StudentPass123!` |
| Administrator | `admin@campus.edu` | `StudentPass123!` |

*(Note: You can also register your own brand-new account anytime at `/register`).*

### Step 7: Start the Flask Development Server
Run the Flask development server (the built-in server is not for production):
```powershell
python app.py
```
You will see output in the terminal:
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### Step 8: Open the Application in Your Browser
Open your web browser (Google Chrome, Microsoft Edge, or Mozilla Firefox) and go to:
[http://127.0.0.1:5000](http://127.0.0.1:5000)

### Step 9: Stopping the Server
When you want to stop the application, return to your PowerShell terminal window and press:
`CTRL + C`

---

## 🧪 Running the Automated Test Suite

To verify all unit and integration tests (covering authentication, item reporting, claim authorization, and AI matching):
```powershell
python -m unittest discover -s tests -v
```

Expected result:
```
Ran 24 tests in 6.4s
OK
```

---

## ❓ Troubleshooting Common Errors

### Error: `Script execution is disabled on this system`
- **Cause**: Windows PowerShell restricts running external scripts by default.
- **Solution**: Run this command once in PowerShell:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

### Error: `Address already in use` or Port 5000 busy
- **Cause**: Another background process or application is occupying port 5000.
- **Solution**: Run the application on an alternate port:
  ```powershell
  flask run --port 5001
  ```
  Then open [http://127.0.0.1:5001](http://127.0.0.1:5001) in your browser.

### Error: `No module named 'flask'`
- **Cause**: You may have installed packages in a different terminal or forgot to activate your virtual environment.
- **Solution**: Activate your virtual environment first (`.\venv\Scripts\Activate.ps1`) and run `pip install -r requirements.txt`.

---

## 🔒 Security Best Practices Implemented

- **Password Hashing**: Passwords are never stored in plaintext. They are salted and cryptographically hashed using Werkzeug's `generate_password_hash` (`scrypt` / `pbkdf2:sha256`).
- **CSRF Protection**: All forms utilize Flask-WTF CSRF tokens to protect against cross-site request forgery.
- **Safe File Uploads**: Image uploads are strictly checked for valid extensions (`.png`, `.jpg`, `.jpeg`, `.webp`), capped at 5MB, inspected using Pillow to verify image headers, and saved with randomized UUID filenames (`uuid4().hex`) to prevent path traversal attacks.
- **Authorization Enforcement**: URL manipulation cannot allow User B to edit or delete User A's reports; server-side permission checks return an HTTP 403 Forbidden.
- **Privacy Protection**: Direct contact details and confidential identifying marks are never exposed on public endpoints.
- **Production Configuration**: Production startup requires a strong `SECRET_KEY` (at least 32 characters) and a configured `DATABASE_URL`; session cookies use secure, HTTP-only, same-site settings. Never use the demo or development credentials in production.
- **Database Migrations**: Use `flask --app app db migrate -m "describe change"` to generate a migration after model changes, review the generated migration, and then apply it with `flask --app app db upgrade`.

Self-registration currently accepts any syntactically valid email address and does not verify ownership of a campus email. Accounts are therefore labeled as student accounts, not verified students. Add an institution-specific domain and email-verification flow before describing accounts as campus-verified.

### Production configuration
Set these variables in the production process or hosting platform; do not use the example secret from `.env.example`:
```powershell
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
$env:DATABASE_URL = "<your production SQLAlchemy database URL>"
$env:FLASK_ENV = "production"
```
Use a production WSGI server to serve the app. `python app.py` intentionally refuses to start when the app is configured for production.
