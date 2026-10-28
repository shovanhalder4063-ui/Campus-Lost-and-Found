from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

# Database instance
db = SQLAlchemy()
migrate = Migrate()

# Authentication & Session Manager
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Please sign in to access this page."
login_manager.login_message_category = "info"

# CSRF Protection
csrf = CSRFProtect()
