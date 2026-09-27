from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import func

from extensions import db
from models import Artwork, Order, OrderItem, Category, AuditLog, User, ArtistProfile, SiteSettings
from forms import CategoryForm, OrderStatusForm, SiteSettingsForm
from decorators import role_required
from utils import upload_url, save_upload

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.app_template_filter("slip_url")
def slip_url_filter(filename):
    return upload_url(current_app.config["SLIP_UPLOAD_SUBDIR"], filename)

@bp.app_template_filter("settings_qr_url")
def settings_qr_url_filter(filename):
    return upload_url(current_app.config["SETTINGS_UPLOAD_SUBDIR"], filename)


@bp.route("/dashboard")
@login_required
@role_required("admin", "staff")
def dashboard():
    total_sales = (
        db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.status.in_(["paid", "shipped", "completed"]))
        .scalar()
    )
    pending_payment = Order.query.filter_by(status="awaiting_payment").count()
    pending_approval = Artwork.query.filter_by(approved=False).count()
    total_orders = Order.query.count()

    top_artists = (
        db.session.query(
            ArtistProfile.display_name,
            func.count(OrderItem.id).label("sold_count"),
            func.coalesce(func.sum(OrderItem.price), 0).label("revenue"),
        )
        .join(Artwork, Artwork.artist_id == ArtistProfile.id)
        .join(OrderItem, OrderItem.artwork_id == Artwork.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status.in_(["paid", "shipped", "completed"]))
        .group_by(ArtistProfile.id)
        .order_by(func.sum(OrderItem.price).desc())
        .limit(5)
        .all()
    )
    # Attach each artist's computed take-home earnings (commission split)
    artist_rows = []
    for name, sold_count, revenue in top_artists:
        profile = ArtistProfile.query.filter_by(display_name=name).first()
        share = profile.commission_rate if profile else 0.8
        artist_rows.append({
            "name": name, "sold_count": sold_count, "revenue": revenue,
            "artist_earnings": round(revenue * share, 2),
            "platform_fee": round(revenue * (1 - share), 2),
        })

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(8).all()

    return render_template(
        "admin_dashboard.html",
        total_sales=total_sales, pending_payment=pending_payment,
        pending_approval=pending_approval, total_orders=total_orders,
        artist_rows=artist_rows, recent_orders=recent_orders,
    )


# ------------------------------------------------------- Artwork approval --

@bp.route("/artworks/pending")
@login_required
@role_required("admin", "staff")
def pending_artworks():
    artworks = Artwork.query.filter_by(approved=False).order_by(Artwork.created_at.asc()).all()
    return render_template("admin_pending.html", artworks=artworks)


@bp.route("/artworks/<int:artwork_id>/approve", methods=["POST"])
@login_required
@role_required("admin", "staff")
def approve_artwork(artwork_id):
    artwork = Artwork.query.get_or_404(artwork_id)
    artwork.approved = True
    AuditLog.record(current_user.id, "update", "artworks", artwork.id, "approved")
    db.session.commit()
    flash(f"อนุมัติผลงาน '{artwork.title}' แล้ว", "success")
    return redirect(url_for("admin.pending_artworks"))


@bp.route("/artworks/<int:artwork_id>/reject", methods=["POST"])
@login_required
@role_required("admin", "staff")
def reject_artwork(artwork_id):
    artwork = Artwork.query.get_or_404(artwork_id)
    AuditLog.record(current_user.id, "delete", "artworks", artwork.id, "rejected by staff")
    db.session.delete(artwork)
    db.session.commit()
    flash("ปฏิเสธและลบผลงานแล้ว", "info")
    return redirect(url_for("admin.pending_artworks"))


# ------------------------------------------------------------- Orders -----

@bp.route("/orders")
@login_required
@role_required("admin", "staff")
def orders():
    status = request.args.get("status", "")
    query = Order.query
    if status:
        query = query.filter_by(status=status)
    orders = query.order_by(Order.created_at.desc()).all()
    return render_template("admin_orders.html", orders=orders, status=status)


@bp.route("/orders/<int:order_id>/confirm-payment", methods=["POST"])
@login_required
@role_required("admin", "staff")
def confirm_payment(order_id):
    order = Order.query.get_or_404(order_id)
    if order.status != "awaiting_payment":
        flash("คำสั่งซื้อนี้ไม่ได้อยู่ในสถานะรอชำระเงิน", "warning")
        return redirect(url_for("admin.orders"))

    from models import now
    order.status = "paid"
    order.confirmed_by_id = current_user.id
    order.confirmed_at = now()
    AuditLog.record(current_user.id, "status_change", "orders", order.id, "awaiting_payment -> paid")
    db.session.commit()
    flash(f"ยืนยันการชำระเงินคำสั่งซื้อ #{order.id} แล้ว", "success")
    return redirect(url_for("admin.orders"))


@bp.route("/orders/<int:order_id>/status", methods=["POST"])
@login_required
@role_required("admin", "staff")
def update_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status")
    valid = {choice for choice, _ in OrderStatusForm().status.choices}
    if new_status in valid:
        old = order.status
        order.status = new_status
        AuditLog.record(current_user.id, "status_change", "orders", order.id, f"{old} -> {order.status}")
        db.session.commit()
        flash(f"อัปเดตสถานะคำสั่งซื้อ #{order.id} แล้ว", "success")
    else:
        flash("สถานะไม่ถูกต้อง", "danger")
    return redirect(url_for("admin.orders"))


# ---------------------------------------------------------- Categories ----

@bp.route("/categories", methods=["GET", "POST"])
@login_required
@role_required("admin", "staff")
def categories():
    form = CategoryForm()
    if form.validate_on_submit():
        if Category.query.filter_by(name=form.name.data).first():
            flash("มีหมวดหมู่นี้อยู่แล้ว", "warning")
        else:
            cat = Category(name=form.name.data)
            db.session.add(cat)
            db.session.flush()
            AuditLog.record(current_user.id, "create", "categories", cat.id, cat.name)
            db.session.commit()
            flash("เพิ่มหมวดหมู่แล้ว", "success")
        return redirect(url_for("admin.categories"))

    all_categories = Category.query.order_by(Category.name).all()
    return render_template("admin_categories.html", form=form, categories=all_categories)


@bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_category(category_id):
    cat = Category.query.get_or_404(category_id)
    if cat.artworks:
        flash("ลบไม่ได้เนื่องจากมีผลงานอยู่ในหมวดหมู่นี้", "danger")
    else:
        AuditLog.record(current_user.id, "delete", "categories", cat.id, cat.name)
        db.session.delete(cat)
        db.session.commit()
        flash("ลบหมวดหมู่แล้ว", "info")
    return redirect(url_for("admin.categories"))


# ------------------------------------------------------------- Users ------

@bp.route("/users")
@login_required
@role_required("admin")
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=all_users)


@bp.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
@role_required("admin")
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get("role")
    if new_role in ("admin", "staff", "customer"):
        old = user.role
        user.role = new_role
        AuditLog.record(current_user.id, "update", "users", user.id, f"role {old} -> {new_role}")
        db.session.commit()
        flash(f"เปลี่ยนสิทธิ์ของ {user.username} เป็น {new_role} แล้ว", "success")
    return redirect(url_for("admin.users"))


# --------------------------------------------------------------- Logs -----

@bp.route("/logs")
@login_required
@role_required("admin")
def logs():
    page = request.args.get("page", 1, type=int)
    pagination = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=30, error_out=False
    )
    return render_template("admin_logs.html", pagination=pagination)

# ----------------------------------------------------- Site settings ------

@bp.route("/settings", methods=["GET", "POST"])
@login_required
@role_required("admin")
def settings():
    site_settings = SiteSettings.get()
    form = SiteSettingsForm(obj=site_settings)

    if form.validate_on_submit():
        site_settings.promptpay_id = form.promptpay_id.data
        site_settings.promptpay_name = form.promptpay_name.data
        if form.qr_image.data:
            filename = save_upload(form.qr_image.data, current_app.config["SETTINGS_UPLOAD_SUBDIR"])
            site_settings.qr_filename = filename
        AuditLog.record(current_user.id, "update", "site_settings", site_settings.id, "updated payment settings")
        db.session.commit()
        flash("บันทึกการตั้งค่าแล้ว", "success")
        return redirect(url_for("admin.settings"))

    return render_template("admin_settings.html", form=form, site_settings=site_settings)
