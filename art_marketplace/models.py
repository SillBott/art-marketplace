from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db


def now():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------- Users ----

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="customer")
    # roles: admin, staff, customer
    created_at = db.Column(db.DateTime, default=now)

    artist_profile = db.relationship(
        "ArtistProfile", back_populates="user", uselist=False,
        cascade="all, delete-orphan",
    )
    # Order has two FKs to User (customer_id, confirmed_by_id), so the
    # join column must be spelled out explicitly on both sides or
    # SQLAlchemy can't tell which FK this relationship should use.
    orders = db.relationship(
        "Order", back_populates="customer", foreign_keys="Order.customer_id"
    )

    def set_password(self, raw):
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password_hash, raw)

    @property
    def is_admin(self):
        return self.role == "admin"

    @property
    def is_staff(self):
        return self.role in ("admin", "staff")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class ArtistProfile(db.Model):
    __tablename__ = "artist_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    display_name = db.Column(db.String(120), nullable=False)
    school = db.Column(db.String(150))
    bio = db.Column(db.Text)
    commission_rate = db.Column(db.Float, default=0.80)  # artist's share, 0-1

    # Each artist's own payment details, shown at checkout for their artworks
    promptpay_id = db.Column(db.String(50))
    promptpay_name = db.Column(db.String(120))
    qr_filename = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=now)

    user = db.relationship("User", back_populates="artist_profile")
    artworks = db.relationship("Artwork", back_populates="artist", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ArtistProfile {self.display_name}>"


# ------------------------------------------------------------ Catalogue ----

class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    artworks = db.relationship("Artwork", back_populates="category")


class Artwork(db.Model):
    __tablename__ = "artworks"

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey("artist_profiles.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)

    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    technique = db.Column(db.String(120))
    size = db.Column(db.String(60))
    price = db.Column(db.Float, nullable=False)

    image_filename = db.Column(db.String(255))           # original / high-res
    preview_filename = db.Column(db.String(255))         # watermarked preview

    status = db.Column(db.String(20), default="available")  # available/sold
    approved = db.Column(db.Boolean, default=False)          # admin/staff gate

    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)

    artist = db.relationship("ArtistProfile", back_populates="artworks")
    category = db.relationship("Category", back_populates="artworks")

    def __repr__(self):
        return f"<Artwork {self.title}>"


# ---------------------------------------------------------------- Orders ----

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    total_amount = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(30), default="awaiting_payment")
    # statuses: awaiting_payment -> paid -> shipped -> completed (or cancelled)

    slip_filename = db.Column(db.String(255))
    confirmed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    confirmed_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=now)
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)

    customer = db.relationship("User", back_populates="orders", foreign_keys=[customer_id])
    confirmed_by = db.relationship("User", foreign_keys=[confirmed_by_id])
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    STATUS_LABELS = {
        "awaiting_payment": "รอชำระเงิน",
        "paid": "ชำระเงินแล้ว",
        "shipped": "จัดส่งแล้ว",
        "completed": "สำเร็จ",
        "cancelled": "ยกเลิก",
    }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    artwork_id = db.Column(db.Integer, db.ForeignKey("artworks.id"), nullable=False)
    price = db.Column(db.Float, nullable=False)  # price at time of purchase

    order = db.relationship("Order", back_populates="items")
    artwork = db.relationship("Artwork")


# ------------------------------------------------------------- Audit log ---

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(50), nullable=False)      # create/update/delete/status_change
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=now)

    user = db.relationship("User")

    @staticmethod
    def record(user_id, action, table_name, record_id, details=""):
        log = AuditLog(
            user_id=user_id, action=action, table_name=table_name,
            record_id=record_id, details=details,
        )
        db.session.add(log)
        return log

# ------------------------------------------------------- Site settings ----

class SiteSettings(db.Model):
    """Single-row table holding the marketplace's own payment details
    (shown to customers at checkout) — not tied to any one user."""
    __tablename__ = "site_settings"

    id = db.Column(db.Integer, primary_key=True)
    promptpay_id = db.Column(db.String(50))       # phone/ID for PromptPay
    promptpay_name = db.Column(db.String(120))     # account holder name shown to buyers
    qr_filename = db.Column(db.String(255))        # uploaded QR code image
    updated_at = db.Column(db.DateTime, default=now, onupdate=now)

    @staticmethod
    def get():
        """Fetch the single settings row, creating an empty one if needed."""
        settings = SiteSettings.query.first()
        if settings is None:
            settings = SiteSettings()
            db.session.add(settings)
            db.session.commit()
        return settings
