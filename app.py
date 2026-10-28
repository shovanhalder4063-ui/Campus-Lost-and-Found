import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit
import mimetypes
from PIL import Image as PILImage

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
    send_from_directory,
    current_app,
)
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.utils import secure_filename
from sqlalchemy import or_

from config import config, BASE_DIR
from extensions import db, login_manager, csrf, migrate
from models import User, Item, Claim
from forms import (
    RegistrationForm,
    LoginForm,
    ReportItemForm,
    ClaimForm,
    CATEGORY_CHOICES,
    ITEM_CATEGORIES,
    CAMPUS_LOCATIONS,
)
from services.matching import get_item_matches, ItemMatcher
from services.storage import (
    StorageError,
    is_storage_configured,
    public_image_url,
    upload_image_to_storage,
)


def is_safe_image_file(file_storage) -> bool:
    """Verify image authenticity and prevent malicious files masquerading as images."""
    try:
        image = PILImage.open(file_storage.stream)
        image.verify()
        file_storage.stream.seek(0)
        return True
    except Exception:
        file_storage.stream.seek(0)
        return False


def save_uploaded_image(file_storage, upload_folder) -> str | None:
    """Safely sanitize, randomize, and store an uploaded image."""
    if not file_storage or not file_storage.filename:
        return None

    filename = secure_filename(file_storage.filename)
    if not filename:
        return None

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in current_app.config["ALLOWED_EXTENSIONS"]:
        return None

    # Verify true file header
    if not is_safe_image_file(file_storage):
        return None

    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    if is_storage_configured(current_app.config):
        image_bytes = file_storage.read()
        content_type = mimetypes.guess_type(unique_filename)[0] or "application/octet-stream"
        upload_image_to_storage(
            current_app.config,
            unique_filename,
            image_bytes,
            content_type,
        )
        return unique_filename

    os.makedirs(upload_folder, exist_ok=True)
    target_path = os.path.join(upload_folder, unique_filename)
    file_storage.save(target_path)
    return unique_filename


def create_app(config_name="default"):
    """Application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config["default"]))
    if config_name == "production":
        secret_key = app.config.get("SECRET_KEY")
        if (
            not secret_key
            or len(secret_key) < 32
            or secret_key == "change-this-to-a-secure-random-secret-key-in-production"
        ):
            raise RuntimeError("Production requires a strong SECRET_KEY of at least 32 characters.")
        if not app.config.get("SQLALCHEMY_DATABASE_URI"):
            raise RuntimeError("Production requires DATABASE_URL to be configured.")
        if not is_storage_configured(app.config):
            app.logger.warning(
                "Supabase Storage is not configured; uploaded images will use "
                "Render's temporary local filesystem until storage is configured."
            )

    # Ensure required runtime folders exist
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    instance_dir = os.path.join(BASE_DIR, "instance")
    os.makedirs(instance_dir, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Template context processors
    @app.context_processor
    def inject_global_vars():
        return {
            "current_year": datetime.now(timezone.utc).year,
            "categories": ITEM_CATEGORIES,
            "category_choices": CATEGORY_CHOICES,
            "campus_locations": CAMPUS_LOCATIONS,
        }

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    @app.errorhandler(413)
    def request_entity_too_large(e):
        flash("File upload exceeds the 5MB size limit. Please choose a smaller image.", "danger")
        return redirect(request.url), 413

    # ==========================================
    # PUBLIC ROUTES
    # ==========================================

    @app.route("/")
    def index():
        """Public homepage with genuine database statistics and recent active reports."""
        # Genuine DB statistics
        total_reports = Item.query.count()
        reunited_count = Item.query.filter_by(status="resolved").count()
        active_lost_count = Item.query.filter_by(report_type="lost", status="active").count()
        active_found_count = Item.query.filter_by(report_type="found", status="active").count()

        # Recent 3 lost and 3 found active items
        recent_lost = (
            Item.query.filter_by(report_type="lost", status="active")
            .order_by(Item.created_at.desc())
            .limit(3)
            .all()
        )
        recent_found = (
            Item.query.filter_by(report_type="found", status="active")
            .order_by(Item.created_at.desc())
            .limit(3)
            .all()
        )

        return render_template(
            "index.html",
            total_reports=total_reports,
            reunited_count=reunited_count,
            active_lost_count=active_lost_count,
            active_found_count=active_found_count,
            recent_lost=recent_lost,
            recent_found=recent_found,
        )

    @app.route("/browse")
    def browse():
        """Browse active item reports with real-time filters, search, and sorting."""
        query_text = request.args.get("q", "").strip()
        report_type = request.args.get("type", "all").strip().lower()
        category = request.args.get("category", "").strip()
        location = request.args.get("location", "").strip()
        sort_by = request.args.get("sort", "newest").strip().lower()
        page = request.args.get("page", 1, type=int)
        per_page = 9

        # Base query: non-deleted items
        item_query = Item.query.filter(Item.status.in_(["active", "pending_return"]))

        # Filter by report_type
        if report_type in ("lost", "found"):
            item_query = item_query.filter(Item.report_type == report_type)

        # Filter by category
        if category:
            item_query = item_query.filter(Item.category == category)

        # Filter by location
        if location:
            item_query = item_query.filter(Item.location.ilike(f"%{location}%"))

        # Search keyword across title, description, and location
        if query_text:
            keyword_filter = or_(
                Item.title.ilike(f"%{query_text}%"),
                Item.description.ilike(f"%{query_text}%"),
                Item.location.ilike(f"%{query_text}%"),
                Item.category.ilike(f"%{query_text}%"),
            )
            item_query = item_query.filter(keyword_filter)

        # Sorting
        if sort_by == "oldest":
            item_query = item_query.order_by(Item.incident_date.asc(), Item.created_at.asc())
        else:
            item_query = item_query.order_by(Item.created_at.desc())

        pagination = item_query.paginate(page=page, per_page=per_page, error_out=False)

        return render_template(
            "browse.html",
            pagination=pagination,
            items=pagination.items,
            current_q=query_text,
            current_type=report_type,
            current_category=category,
            current_location=location,
            current_sort=sort_by,
        )

    @app.route("/item/<int:item_id>")
    def item_detail(item_id):
        """Display item details, safe poster attribution, and potential matches."""
        item = db.get_or_404(Item, item_id)
        claim_form = ClaimForm()

        is_owner = current_user.is_authenticated and current_user.id == item.user_id
        is_admin = current_user.is_authenticated and current_user.is_admin

        # Check existing claim if user is logged in
        user_claim = None
        if current_user.is_authenticated and not is_owner:
            user_claim = Claim.query.filter_by(item_id=item.id, claimant_id=current_user.id).first()

        # Retrieve AI matches (comparing against active items of opposite type)
        all_opposite = (
            Item.query.filter(
                Item.id != item.id,
                Item.report_type != item.report_type,
                Item.status == "active",
            )
            .limit(40)
            .all()
        )
        ai_matches = get_item_matches(item, all_opposite, min_score=0.15, top_k=3)

        # Retrieve claims if owner or admin
        claims = []
        if is_owner or is_admin:
            claims = item.claims.order_by(Claim.created_at.desc()).all()

        return render_template(
            "item_detail.html",
            item=item,
            claim_form=claim_form,
            is_owner=is_owner,
            is_admin=is_admin,
            user_claim=user_claim,
            claims=claims,
            ai_matches=ai_matches,
        )

    @app.route("/uploads/<filename>")
    def uploaded_file(filename):
        """Serve stored photographs or redirect to their public Supabase Storage URL."""
        safe_name = secure_filename(filename)
        if safe_name != filename:
            return redirect(url_for("static", filename="images/placeholder.svg"))

        if is_storage_configured(app.config):
            return redirect(public_image_url(app.config, safe_name))

        file_path = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
        if not os.path.isfile(file_path):
            return redirect(url_for("static", filename="images/placeholder.svg"))
        return send_from_directory(app.config["UPLOAD_FOLDER"], safe_name)

    # ==========================================
    # AUTHENTICATION ROUTES
    # ==========================================

    @app.route("/register", methods=["GET", "POST"])
    def register():
        """User registration with password validation and duplicate check."""
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        form = RegistrationForm()
        if form.validate_on_submit():
            existing_user = User.query.filter_by(email=form.email.data.strip().lower()).first()
            if existing_user:
                flash("An account with this email address already exists. Please sign in.", "warning")
                return redirect(url_for("login"))

            user = User(
                name=form.name.data.strip(),
                email=form.email.data.strip().lower(),
                role="student",
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()

            flash("Account successfully created! You can now log in.", "success")
            return redirect(url_for("login"))

        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """User login with generic error messages for credential protection."""
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data.strip().lower()).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember_me.data)
                flash(f"Welcome back, {user.name}!", "success")
                next_page = request.args.get("next")
                if next_page and is_safe_local_redirect(next_page):
                    return redirect(next_page)
                return redirect(url_for("dashboard"))

            # Generic error prevents account enumeration
            flash("Invalid email or password. Please verify your credentials.", "danger")

        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        """Sign out the currently authenticated user."""
        logout_user()
        flash("You have been successfully signed out.", "info")
        return redirect(url_for("index"))

    # ==========================================
    # ITEM REPORTING & MANAGEMENT ROUTES
    # ==========================================

    @app.route("/report/lost", methods=["GET", "POST"])
    @login_required
    def report_lost():
        """Shortcut route to report a lost item."""
        form = ReportItemForm()
        form.report_type.data = "lost"
        return handle_report_submission(form, default_type="lost")

    @app.route("/report/found", methods=["GET", "POST"])
    @login_required
    def report_found():
        """Shortcut route to report a found item."""
        form = ReportItemForm()
        form.report_type.data = "found"
        return handle_report_submission(form, default_type="found")

    def handle_report_submission(form, default_type="lost"):
        """Shared logic for submitting item reports."""
        if form.validate_on_submit():
            image_filename = None
            if form.image.data and hasattr(form.image.data, "filename") and form.image.data.filename:
                try:
                    image_filename = save_uploaded_image(form.image.data, app.config["UPLOAD_FOLDER"])
                except StorageError:
                    current_app.logger.exception("Supabase Storage image upload failed.")
                    flash("Image upload failed. Please try again later.", "danger")
                    return render_template("report_item.html", form=form, report_type=default_type)
                if not image_filename and form.image.data.filename:
                    flash("Invalid or corrupted image file. Please upload a valid PNG, JPG, or WebP image.", "danger")
                    return render_template("report_item.html", form=form, report_type=default_type)

            item = Item(
                user_id=current_user.id,
                title=form.title.data.strip(),
                description=form.description.data.strip(),
                category=form.category.data,
                report_type=form.report_type.data,
                incident_date=form.incident_date.data,
                location=form.location.data.strip(),
                image_filename=image_filename,
                private_details=form.private_details.data.strip() if form.private_details.data else None,
                status="active",
            )
            db.session.add(item)
            db.session.commit()

            type_label = "Lost item report" if item.report_type == "lost" else "Found item report"
            flash(f"{type_label} published successfully! Our AI is actively scanning for matches.", "success")
            return redirect(url_for("item_detail", item_id=item.id))

        return render_template("report_item.html", form=form, report_type=default_type)

    @app.route("/item/<int:item_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_item(item_id):
        """Allow the item poster or admin to edit listing details."""
        item = db.get_or_404(Item, item_id)
        if item.user_id != current_user.id and not current_user.is_admin:
            abort(403)

        form = ReportItemForm(obj=item)

        if form.validate_on_submit():
            new_image = None
            if form.image.data and getattr(form.image.data, "filename", ""):
                try:
                    new_image = save_uploaded_image(form.image.data, app.config["UPLOAD_FOLDER"])
                except StorageError:
                    current_app.logger.exception("Supabase Storage image upload failed.")
                    flash("Image upload failed. Please try again later.", "danger")
                    return render_template("edit_item.html", form=form, item=item)
                if not new_image:
                    flash(
                        "Invalid or corrupted image file. Please upload a valid PNG, JPG, or WebP image.",
                        "danger",
                    )
                    return render_template("edit_item.html", form=form, item=item)

            item.title = form.title.data.strip()
            item.category = form.category.data
            item.report_type = form.report_type.data
            item.incident_date = form.incident_date.data
            item.location = form.location.data.strip()
            item.description = form.description.data.strip()
            item.private_details = form.private_details.data.strip() if form.private_details.data else None

            if new_image:
                item.image_filename = new_image

            db.session.commit()
            flash("Listing details have been successfully updated.", "success")
            return redirect(url_for("item_detail", item_id=item.id))

        return render_template("edit_item.html", form=form, item=item)

    @app.route("/item/<int:item_id>/status", methods=["POST"])
    @login_required
    def update_item_status(item_id):
        """Update item listing status (active, resolved, closed)."""
        item = Item.query.get_or_404(item_id)
        if item.user_id != current_user.id and not current_user.is_admin:
            abort(403)

        new_status = request.form.get("status")
        valid_statuses = ["active", "pending_return", "resolved", "closed"]
        if new_status in valid_statuses:
            item.status = new_status
            db.session.commit()
            status_labels = {
                "active": "marked as Active",
                "pending_return": "marked as Pending Return",
                "resolved": "marked as Reunited / Resolved 🎉",
                "closed": "closed",
            }
            flash(f"Item #{item.id} has been {status_labels.get(new_status, new_status)}.", "success")
        else:
            flash("Invalid status specified.", "danger")

        return redirect(request.referrer or url_for("item_detail", item_id=item.id))

    @app.route("/item/<int:item_id>/delete", methods=["POST"])
    @login_required
    def delete_item(item_id):
        """Delete an item report (owner or admin only)."""
        item = db.get_or_404(Item, item_id)
        if item.user_id != current_user.id and not current_user.is_admin:
            abort(403)

        db.session.delete(item)
        db.session.commit()
        flash("Item listing has been permanently removed.", "info")
        return redirect(url_for("dashboard"))

    # ==========================================
    # CLAIM WORKFLOW ROUTES
    # ==========================================

    @app.route("/item/<int:item_id>/claim", methods=["POST"])
    @login_required
    def submit_claim(item_id):
        """Submit an ownership claim for an item."""
        item = db.get_or_404(Item, item_id)

        # Security Checks
        if item.user_id == current_user.id:
            flash("You cannot submit an ownership claim on your own listing.", "warning")
            return redirect(url_for("item_detail", item_id=item.id))

        if item.status in ("resolved", "closed"):
            flash("This listing has already been resolved or closed. No new claims can be filed.", "warning")
            return redirect(url_for("item_detail", item_id=item.id))

        # Check existing pending claim from same user
        existing_claim = Claim.query.filter_by(
            item_id=item.id,
            claimant_id=current_user.id,
            status="pending"
        ).first()
        if existing_claim:
            flash("You already have an active pending claim for this item. Please wait for the poster to respond.", "info")
            return redirect(url_for("item_detail", item_id=item.id))

        form = ClaimForm()
        if form.validate_on_submit():
            claim = Claim(
                item_id=item.id,
                claimant_id=current_user.id,
                message=form.message.data.strip(),
                status="pending",
            )
            db.session.add(claim)
            db.session.commit()

            flash("Your ownership claim has been submitted to the poster for verification.", "success")
            return redirect(url_for("item_detail", item_id=item.id))

        flash("Please provide a valid claim message explaining your ownership.", "danger")
        return redirect(url_for("item_detail", item_id=item.id))

    @app.route("/claim/<int:claim_id>/<action>", methods=["POST"])
    @login_required
    def manage_claim(claim_id, action):
        """Poster or admin review: approve or reject a claim."""
        claim = db.get_or_404(Claim, claim_id)
        item = claim.item

        # Authorization check: only the item poster or an admin
        if item.user_id != current_user.id and not current_user.is_admin:
            abort(403)

        if action == "approve":
            if claim.status != "pending" or item.status != "active":
                flash("Only pending claims on active listings can be approved.", "warning")
                return redirect(request.referrer or url_for("item_detail", item_id=item.id))
            claim.status = "approved"
            item.status = "pending_return"
            Claim.query.filter(
                Claim.item_id == item.id,
                Claim.id != claim.id,
                Claim.status == "pending",
            ).update({Claim.status: "rejected"}, synchronize_session=False)
            db.session.commit()
            flash(f"Claim #{claim.id} approved! You can now coordinate handover with {claim.claimant.safe_display_name}.", "success")
        elif action == "reject":
            if claim.status != "pending":
                flash("Only pending claims can be rejected.", "warning")
                return redirect(request.referrer or url_for("item_detail", item_id=item.id))
            claim.status = "rejected"
            db.session.commit()
            flash(f"Claim #{claim.id} has been rejected.", "info")
        elif action == "resolve":
            if claim.status != "approved" or item.status != "pending_return":
                flash("Only an approved claim awaiting handover can be resolved.", "warning")
                return redirect(request.referrer or url_for("item_detail", item_id=item.id))
            claim.status = "resolved"
            item.status = "resolved"
            db.session.commit()
            flash(f"Handover confirmed! Item #{item.id} has been marked as Reunited/Resolved.", "success")
        else:
            flash("Invalid claim action.", "danger")

        return redirect(request.referrer or url_for("item_detail", item_id=item.id))

    # ==========================================
    # USER DASHBOARD & AI MATCHING EXPLORER
    # ==========================================

    @app.route("/dashboard")
    @login_required
    def dashboard():
        """User dashboard displaying reports, submitted claims, received claims, and AI recommendations."""
        my_lost_items = (
            Item.query.filter_by(user_id=current_user.id, report_type="lost")
            .order_by(Item.created_at.desc())
            .all()
        )
        my_found_items = (
            Item.query.filter_by(user_id=current_user.id, report_type="found")
            .order_by(Item.created_at.desc())
            .all()
        )

        my_submitted_claims = (
            Claim.query.filter_by(claimant_id=current_user.id)
            .order_by(Claim.created_at.desc())
            .all()
        )

        # Incoming claims on items posted by current user
        user_item_ids = [item.id for item in current_user.items]
        incoming_claims = (
            Claim.query.filter(Claim.item_id.in_(user_item_ids))
            .order_by(Claim.created_at.desc())
            .all()
            if user_item_ids
            else []
        )

        # Collect AI recommendations for all user's active items
        active_user_items = [it for it in current_user.items if it.is_active]
        ai_recommendations = []
        if active_user_items:
            # Load candidate items of opposite types
            all_active_items = Item.query.filter_by(status="active").all()
            matcher = ItemMatcher(min_score=0.15, top_k=3)
            for user_item in active_user_items:
                matches = matcher.find_matches(user_item, all_active_items)
                if matches:
                    ai_recommendations.append({
                        "user_item": user_item,
                        "matches": matches
                    })

        return render_template(
            "dashboard.html",
            my_lost_items=my_lost_items,
            my_found_items=my_found_items,
            my_submitted_claims=my_submitted_claims,
            incoming_claims=incoming_claims,
            ai_recommendations=ai_recommendations,
        )

    @app.route("/matches")
    @login_required
    def matches_explorer():
        """Dedicated AI Matching Hub with side-by-side match viewer and transparent scoring breakdown."""
        user_active_items = (
            Item.query.filter_by(user_id=current_user.id, status="active")
            .order_by(Item.created_at.desc())
            .all()
        )

        selected_item_id = request.args.get("item_id", type=int)
        selected_item = None
        match_results = []

        if selected_item_id:
            selected_item = db.session.get(Item, selected_item_id)
            if selected_item and (selected_item.user_id == current_user.id or current_user.is_admin):
                all_active_candidates = (
                    Item.query.filter(
                        Item.id != selected_item.id,
                        Item.report_type != selected_item.report_type,
                        Item.status == "active",
                    ).all()
                )
                match_results = get_item_matches(selected_item, all_active_candidates, min_score=0.10, top_k=6)
        elif user_active_items:
            selected_item = user_active_items[0]
            all_active_candidates = (
                Item.query.filter(
                    Item.id != selected_item.id,
                    Item.report_type != selected_item.report_type,
                    Item.status == "active",
                ).all()
            )
            match_results = get_item_matches(selected_item, all_active_candidates, min_score=0.10, top_k=6)

        return render_template(
            "matches.html",
            user_items=user_active_items,
            selected_item=selected_item,
            matches=match_results,
        )

    # ==========================================
    # CLI UTILITIES & DATABASE INITIALIZATION
    # ==========================================

    @app.cli.command("create-admin")
    def create_admin():
        """Create or promote a designated campus administrator."""
        email = input("Admin Email: ").strip().lower()
        name = input("Admin Name: ").strip()
        password = input("Admin Password: ").strip()

        if len(password) < 8:
            print("Password must be at least 8 characters.")
            return

        user = User.query.filter_by(email=email).first()
        if user:
            user.role = "admin"
            user.set_password(password)
            print(f"User {email} updated to Admin role.")
        else:
            user = User(name=name, email=email, role="admin")
            user.set_password(password)
            db.session.add(user)
            print(f"Admin user {email} created successfully.")
        db.session.commit()

    return app


# Application instance for running with `flask run` or `python app.py`
app = create_app(os.environ.get("FLASK_ENV", "development"))


def is_safe_local_redirect(target: str) -> bool:
    """Only allow redirect targets that stay on this site."""
    try:
        parsed = urlsplit(target)
    except ValueError:
        return False
    return (
        target.startswith("/")
        and not target.startswith("//")
        and "\\" not in target
        and not parsed.scheme
        and not parsed.netloc
    )


if __name__ == "__main__":
    if not app.config["DEBUG"]:
        raise RuntimeError("The built-in server is for development only; run production with a WSGI server.")
    app.run(host="127.0.0.1", port=5000, debug=app.config["DEBUG"])
