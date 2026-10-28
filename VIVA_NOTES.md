# Viva Voce & Technical Defense Notes: Campus Lost & Found Portal 🎓📋

This document is prepared for the second-year B.Tech Computer Science and Engineering (Data Science) academic evaluation and project viva voce examination. It provides in-depth, plain-English explanations of the problem, software architecture, mathematical matching logic, database design, and likely examiner questions.

---

## 1. Project Overview & Problem Statement

### The Problem
On university and college campuses, hundreds of personal belongings—student identity cards, laptop chargers, scientific calculators, water bottles, earphones, and notebooks—are misplaced every semester. The traditional recovery mechanisms suffer from significant flaws:
- **Scattered Communication**: Lost items are posted randomly on WhatsApp groups, informal Telegram channels, Instagram stories, or pinned to physical notice boards where they are quickly buried or missed.
- **Privacy Vulnerabilities**: Students openly post their phone numbers, roll numbers, or personal email addresses, inviting harassment or fake claims.
- **Lack of Verification**: Finders have no structured mechanism to verify if a claimant is the true owner before handing over valuable property.
- **No Automated Correlation**: Finders and losers must manually read every post to notice that a "Dell adapter found in Library" corresponds to a "Laptop charger lost on 2nd floor".

### The Solution
The **Campus Lost & Found Portal** provides a centralized, secure web application where:
1. Reports are categorized, indexed, and filterable.
2. A **Confidential Verification Vault** allows posters to store secret identifying marks (like serial numbers or hidden scratches) visible only to them and moderators.
3. A local **AI Matching Engine** automatically correlates lost and found reports using Natural Language Processing (TF-IDF vectorization and Cosine Similarity) combined with contextual campus metadata.
4. An integrated **Claim Verification Workflow** prevents unauthorized claims and enables secure campus handovers.

---

## 2. System Architecture

```
+-------------------------------------------------------------------------+
|                              CLIENT TIER                                |
|  - HTML5 & CSS3 Design System (Warm off-white, deep teal, rounded cards)|
|  - Vanilla JavaScript (Dynamic tabs, photo preview, Lucide icons)       |
+------------------------------------+------------------------------------+
                                     | HTTP / HTTPS Requests
                                     v
+-------------------------------------------------------------------------+
|                           APPLICATION TIER                              |
|  - Python 3 / Flask Microframework                                     |
|  - Flask-Login (Session management, user authentication)               |
|  - Flask-WTF & WTForms (Input validation, CSRF tokens)                  |
|  - Pillow (Image header inspection, upload protection)                  |
+------------------------------------+------------------------------------+
                                     |
            +------------------------+------------------------+
            | Queries & Transactions                          | Feature Extraction
            v                                                 v
+-----------------------+                         +-----------------------+
|     DATABASE TIER     |                         |   AI MATCHING ENGINE  |
|  - SQLite3 Database   |                         |  - scikit-learn       |
|  - Flask-SQLAlchemy   |                         |  - TF-IDF Vectorizer  |
|  - Models:            |                         |  - Cosine Similarity  |
|    * User             |                         |  - Contextual Bonuses |
|    * Item             |                         |    (Category, Location|
|    * Claim            |                         |     Date Proximity)   |
+-----------------------+                         +-----------------------+
```

### Component Responsibilities:
- **Frontend (Templates & Static Assets)**: Renders dynamic server-side pages via Jinja2 templates, handles client-side file validation, provides smooth mobile navigation, and displays honest AI match chips.
- **Backend (Flask Application)**: Implements business logic, session handling, access control checks, image processing with randomized UUID filenames, and RESTful routing.
- **Database (SQLite & SQLAlchemy ORM)**: Stores relational data safely with constraints, primary keys, foreign keys, and cascading relationships.
- **AI Matching Module (`services/matching.py`)**: Runs entirely in Python without external paid APIs; transforms text into numerical vectors and evaluates relevance.

---

## 3. Database Schema & Relational Design

The database uses three normalized tables linked via Foreign Key constraints:

```
+--------------------+        1 : N         +--------------------+
|       USERS        | -------------------> |       ITEMS        |
+--------------------+                      +--------------------+
| id (PK)            |                      | id (PK)            |
| name               |                      | user_id (FK)       |
| email (Unique)     |                      | title              |
| password_hash      |                      | description        |
| role ('student')   |                      | category           |
| created_at         |                      | report_type        |
+--------------------+                      | incident_date      |
          |                                 | location           |
          | 1 : N                           | image_filename     |
          |                                 | private_details    |
          v                                 | status             |
+--------------------+        N : 1         | created_at         |
|       CLAIMS       | <------------------- | updated_at         |
+--------------------+                      +--------------------+
| id (PK)            |
| item_id (FK)       |
| claimant_id (FK)   |
| message            |
| status ('pending') |
| created_at         |
| updated_at         |
+--------------------+
```

### Key Schema Design Decisions:
1. **`private_details` Column**: Stored inside the `Item` model, but explicitly filtered in templates so that claimant users never see it.
2. **`password_hash`**: Stores a 256-character cryptographically salted hash produced by Werkzeug's `generate_password_hash` function. Plaintext passwords are never persisted.
3. **Cascading Deletes**: If an item is permanently deleted, all related claims are automatically cleaned up (`cascade="all, delete-orphan"`), preventing orphaned records.

---

## 4. How the AI Matching Algorithm Works (In Detail)

The matching engine in `services/matching.py` implements a hybrid scoring pipeline combining **Natural Language Processing (NLP)** with **Heuristic Feature Scoring**:

### Step 1: Text Corpus Normalization
For both the target item and candidate opposite items, public text fields (`title`, `category`, `description`, `location`) are combined and normalized:
- Lowercased
- Punctuation removed
- Whitespaces collapsed
- *Crucially, private verification details and passwords are NEVER included in this corpus.*

### Step 2: TF-IDF Vectorization
**TF-IDF** stands for **Term Frequency - Inverse Document Frequency**:
1. **Term Frequency ($TF$)**: Measures how frequently a word appears in a specific item report:
   $$TF(t, d) = \frac{\text{Count of term } t \text{ in report } d}{\text{Total words in report } d}$$
2. **Inverse Document Frequency ($IDF$)**: Measures how unique or informative a word is across all campus reports:
   $$IDF(t) = \ln\left(\frac{1 + N}{1 + DF(t)}\right) + 1$$
   *(Common words like "the", "found", "lost" get low weights, whereas specific keywords like "Dell", "Calculus", "Casio", "Hydro" get high weights).*
3. **TF-IDF Weight**:
   $$\text{TF-IDF}(t, d) = TF(t, d) \times IDF(t)$$
4. The scikit-learn `TfidfVectorizer` converts each item text into a high-dimensional mathematical vector $\mathbf{v} \in \mathbb{R}^V$.

### Step 3: Cosine Similarity
To measure how closely the descriptions align regardless of text length, we compute the **Cosine Similarity** between the target vector $\mathbf{u}$ and candidate vector $\mathbf{v}$:
$$\text{Cosine Similarity}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2} = \frac{\sum_{i=1}^V u_i v_i}{\sqrt{\sum_{i=1}^V u_i^2} \sqrt{\sum_{i=1}^V v_i^2}}$$
- If two texts share identical words and phrasing: $\text{Cosine Similarity} \approx 1.0$.
- If two texts share no vocabulary: $\text{Cosine Similarity} = 0.0$.

### Step 4: Contextual Relevance Adjustments
Text similarity alone can be fooled by generic words. Therefore, our algorithm adds deterministic contextual adjustments:
1. **Category Agreement**: If `target.category == candidate.category`, add $+0.15$ ($15\%$).
2. **Location Proximity**: If locations match exactly ($+0.12$) or share significant campus tokens like "Library", "Cafeteria", "Block A" ($+0.08$).
3. **Incident Date Proximity**:
   - Exact same date: $+0.08$
   - Within 3 days: $+0.05$
   - Within 7 days: $+0.02$

### Step 5: Composite Scoring & Normalization
$$\text{Composite Score} = (\text{Cosine Score} \times 0.65) + \text{Category Bonus} + \text{Location Bonus} + \text{Date Bonus}$$
- Bounded strictly between $0.0$ and $1.0$ ($0\% - 100\%$).
- Thresholded at $\ge 0.15$ to filter out irrelevant noise.
- Transparently labeled as **"Potential Match"** along with the specific reasons (e.g. *"Exact category match"*, *"Reported on same date"*).

---

## 5. Security & Privacy Safeguards

1. **Password Security**: Uses salted cryptographic password hashing (`scrypt` / `pbkdf2:sha256`).
2. **Access Control (Authorization)**: Every modification checks `if item.user_id != current_user.id and not current_user.is_admin: abort(403)`. A user cannot alter another student's report by tampering with URL parameters.
3. **CSRF Protection**: All form submissions enforce cryptographic tokens verified by `Flask-WTF`.
4. **Malicious Upload Mitigation**:
   - Files are validated against an allowed extension whitelist (`.png`, `.jpg`, `.jpeg`, `.webp`).
   - Pillow (`PIL.Image.verify()`) inspects file byte headers to ensure an executable or script hasn't been disguised with a `.jpg` extension.
   - Files are saved with random UUID hexadecimal names (`uuid4().hex`) to prevent directory traversal attacks (`../../evil.php`).
   - File size is hard-capped at 5MB via Flask configuration.
5. **Private Vault**: Sensitive identifying features are isolated from public browse listings and public search queries.

---

## 6. Testing & Quality Assurance

A comprehensive automated test suite of **19 test cases** was written using Python's `unittest` framework:
- **Authentication Tests (`test_auth.py`)**: Validates registration, duplicate email rejection, password hashing secrecy, valid/invalid login flash messages, and session logout.
- **Item Management Tests (`test_items.py`)**: Tests lost report creation, found report creation, search filters by keyword, report type, and category, and enforces HTTP 403 authorization defense against unauthorized edits.
- **Claim Workflow Tests (`test_claims.py`)**: Tests submission of claims, verifies that users cannot claim their own listings, verifies that duplicate pending claims are prevented, and tests the poster approval-to-resolution lifecycle.
- **AI Matching Tests (`test_matching.py`)**: Tests similar descriptions with distinct vocabulary, totally unrelated items (zero false matches), exclusion of same-type reports, exclusion of self-matching, exclusion of resolved items, and robust handling of empty text and empty databases.

---

## 7. Top 15 Viva Voce Questions & Answers

### Q1: What is the main objective of your project?
**Answer**: The main objective is to provide a secure, centralized web platform for university campuses that reduces the friction of reuniting lost belongings with their owners. Its unique differentiator is an explainable local AI matching engine that correlates lost and found reports using text similarity and metadata heuristics without exposing student contact information.

### Q2: Why did you choose Flask over Django or Node.js?
**Answer**: Flask is a lightweight, Python-based microframework that offers simplicity, transparency, and explicit control. Because our AI matching logic relies on Python's scientific ecosystem (`scikit-learn` and `numpy`), building the backend in Flask allows native, in-memory vectorization without requiring inter-process communication or external microservices.

### Q3: How does the AI matching feature work?
**Answer**: It converts the item's title, category, location, and description into numerical vectors using `TfidfVectorizer`. It then calculates the Cosine Similarity between a lost report and eligible found reports. Finally, it applies contextual weight bonuses for category agreement ($+15\%$), campus location overlap ($+8-12\%$), and incident date proximity ($+2-8\%$) to rank potential candidates.

### Q4: What does TF-IDF mean mathematically?
**Answer**: TF-IDF stands for Term Frequency-Inverse Document Frequency. Term Frequency ($TF$) measures the density of a term in a specific document. Inverse Document Frequency ($IDF$) measures how rare or informative that word is across the entire collection of documents:
$$IDF(t) = \ln\left(\frac{1+N}{1+DF(t)}\right) + 1$$
Multiplying $TF \times IDF$ assigns high importance to distinct keywords (like "Dell", "Calculus") while minimizing insignificant common words.

### Q5: What is Cosine Similarity and why is it preferred over Euclidean Distance?
**Answer**: Cosine Similarity measures the cosine of the angle between two multi-dimensional vectors:
$$\cos(\theta) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\| \|\mathbf{v}\|}$$
It evaluates directional orientation rather than magnitude. This is ideal for lost and found reports because one student might write a brief 5-word description while another writes a 50-word description; Cosine Similarity normalizes for document length, whereas Euclidean distance would penalize length differences.

### Q6: Does your AI require an internet connection or paid OpenAI API key?
**Answer**: No. The AI algorithm runs 100% locally on the host server using `scikit-learn`. It requires no third-party APIs, no monthly subscriptions, zero network latency, and poses zero privacy risk of sending student data to external commercial cloud providers.

### Q7: Why do you label suggestions as "Potential Match" instead of "Confirmed Match"?
**Answer**: Because text similarity is a heuristic indicator, not absolute proof of ownership. Declaring a confirmed match algorithmically would risk fraudulent handovers. Human verification through the claim workflow and confidential identifying marks remains essential.

### Q8: How is student privacy protected on the platform?
**Answer**: First, student emails and telephone numbers are not publicly displayed. Second, the portal features a **Confidential Verification Vault** where posters can note secret marks (serial numbers, hidden scratches, specific wallpapers) that are stored in the database but strictly hidden from public templates and only accessible to the reporter and moderators.

### Q9: How are passwords stored securely?
**Answer**: Passwords are never stored in plaintext. When a student registers, Werkzeug's `generate_password_hash()` creates a cryptographically salted one-way hash using modern algorithms (`scrypt` or `pbkdf2:sha256`). During login, `check_password_hash()` verifies the entered password against the stored salt and hash.

### Q10: How do you prevent cross-site request forgery (CSRF)?
**Answer**: We implement `Flask-WTF` CSRF protection. Every state-altering HTTP form includes a hidden, time-sensitive cryptographic `csrf_token` linked to the user's session cookie. Submissions lacking a valid token are rejected with HTTP 400 Bad Request.

### Q11: What happens if a malicious user uploads a script or virus renamed as an image?
**Answer**: We implement a 3-layer upload security protocol:
1. File extension validation against an allowed whitelist (`.png`, `.jpg`, `.jpeg`, `.webp`).
2. Pillow library verification (`PIL.Image.verify()`) which inspects binary image headers to ensure genuine raster data.
3. Storing files with a cryptographically randomized UUID name (`uuid4().hex`) to prevent path traversal and execution vulnerabilities.

### Q12: Can a user modify another student's report by changing the ID in the URL?
**Answer**: No. On every edit, status change, and delete endpoint, our backend enforces server-side authorization:
```python
if item.user_id != current_user.id and not current_user.is_admin:
    abort(403)
```
If an unauthorized student attempts access, Flask halts execution immediately and raises an HTTP 403 Forbidden error.

### Q13: What prevents students from spamming false claims?
**Answer**: 
1. A user is prevented from claiming their own item.
2. The database query verifies whether the student already has an active pending claim on that item:
```python
existing_claim = Claim.query.filter_by(item_id=item.id, claimant_id=current_user.id, status="pending").first()
```
3. Claims require substantive explanation text (minimum 15 characters).
4. The poster can review and reject fraudulent claims with a single click.

### Q14: What are the technical limitations of this prototype?
**Answer**: 
1. **Vocabulary / Synonym Limitations**: TF-IDF relies on keyword overlap. If one student writes "mobile phone" and another writes "cellphone", TF-IDF alone won't detect lexical synonymy (though our category and location boosts mitigate this).
2. **Local Storage**: Uploaded images are stored in a local directory rather than distributed object storage (like AWS S3).
3. **Absence of Push Notifications**: Notifications are session-based rather than sending automated email or SMS alerts.

### Q15: How can this system be enhanced in future versions?
**Answer**:
1. Upgrading from TF-IDF to transformer-based sentence embeddings (such as HuggingFace `all-MiniLM-L6-v2`) for semantic synonym comprehension.
2. Integrating computer vision embeddings (e.g., CLIP) to compare image features of lost and found items.
3. Adding university Single Sign-On (SSO) via SAML/OAuth to restrict registration to official campus email domains.
4. Implementing automated email notifications upon receiving a new claim or high-confidence AI match.
