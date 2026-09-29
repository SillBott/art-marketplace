import os
from flask import Blueprint, render_template, redirect, url_for, flash, current_app, session, abort, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from extensions import db
from models import Order, OrderItem, Artwork, AuditLog, SiteSettings
from forms import CheckoutForm
from utils import save_upload
from routes.cart import CART_KEY

bp = Blueprint("orders", __name__, url_prefix="/orders")

# Order statuses that mean payment has been confirmed — a buyer's purchase
# unlocks the full-resolution download from this point on.
UNLOCKED_STATUSES = ("paid", "shipped", "completed")


@bp.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    ids = session.get(CART_KEY, [])
    artworks = Artwork.query.filter(Artwork.id.in_(ids)).all() if ids else []
    items = [a for a in artworks if a.status == "available"]

    if not items:
        flash("ตะกร้าว่างหรือผลงานถูกขายไปแล้ว", "warning")
        return redirect(url_for("cart.view"))

    total = sum(a.price for a in items)
    form = CheckoutForm()

    artist = items[0].artist
    if artist.promptpay_id or artist.qr_filename:
        payment_info = {
            "label": f"{artist.display_name} (ศิลปิน)",
            "promptpay_id": artist.promptpay_id,
            "promptpay_name": artist.promptpay_name or artist.display_name,
            "qr_filename": artist.qr_filename,
        }
    else:
        site_settings = SiteSettings.get()
        payment_info = {
            "label": "ร้านค้า (ยังไม่ได้ตั้งค่าบัญชีศิลปิน)",
            "promptpay_id": site_settings.promptpay_id,
            "promptpay_name": site_settings.promptpay_name,
            "qr_filename": site_settings.qr_filename,
        }
    if form.validate_on_submit():
        # Re-check availability at the last moment to avoid double-selling
        still_available = [a for a in items if a.status == "available"]
        if not still_available:
            flash("ผลงานทั้งหมดถูกขายไปแล้ว", "danger")
            return redirect(url_for("cart.view"))

        order = Order(customer_id=current_user.id, total_amount=sum(a.price for a in still_available))
        slip_filename = save_upload(form.slip.data, current_app.config["SLIP_UPLOAD_SUBDIR"])
        order.slip_filename = slip_filename
        db.session.add(order)
        db.session.flush()

        for artwork in still_available:
            db.session.add(OrderItem(order_id=order.id, artwork_id=artwork.id, price=artwork.price))
            artwork.status = "sold"

        AuditLog.record(current_user.id, "create", "orders", order.id, f"total={order.total_amount}")
        db.session.commit()

        session[CART_KEY] = []
        flash("ส่งคำสั่งซื้อแล้ว รอแอดมินตรวจสอบสลิป", "success")
        return redirect(url_for("orders.detail", order_id=order.id))

    return render_template("checkout.html", form=form, items=items, total=total, payment_info=payment_info)


@bp.route("/")
@login_required
def my_orders():
    orders = (
        Order.query.filter_by(customer_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template("my_orders.html", orders=orders)


@bp.route("/<int:order_id>")
@login_required
def detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.customer_id != current_user.id and not current_user.is_staff:
        abort(403)
    return render_template("order_detail.html", order=order)

################# Collection #########################
@bp.route("/collection")
@login_required
def collection():
    """Every artwork the current user has successfully bought (payment
    confirmed), deduplicated, newest purchase first — with a download link."""
    items = (
        OrderItem.query.join(Order)
        .filter(
            Order.customer_id == current_user.id,
            Order.status.in_(UNLOCKED_STATUSES),
        )
        .order_by(Order.created_at.desc())
        .all()
    )
    seen = {}
    for item in items:
        seen.setdefault(item.artwork_id, item)
    return render_template("my_collection.html", items=list(seen.values()))


@bp.route("/artwork/<int:artwork_id>/download")
@login_required
def download_artwork(artwork_id):
    """Serve the original (non-watermarked) file — only to a buyer who
    actually owns a paid/shipped/completed order containing it."""
    owns_it = (
        OrderItem.query.join(Order)
        .filter(
            OrderItem.artwork_id == artwork_id,
            Order.customer_id == current_user.id,
            Order.status.in_(UNLOCKED_STATUSES),
        )
        .first()
    )
    if not owns_it:
        abort(403)

    artwork = Artwork.query.get_or_404(artwork_id)
    filename = artwork.image_filename
    if not filename:
        abort(404)

    # Cloudinary-stored files are already full URLs — just send the buyer there.
    if filename.startswith("http://") or filename.startswith("https://"):
        return redirect(filename)

    ext = filename.rsplit(".", 1)[-1]
    download_name = f"{secure_filename(artwork.title) or 'artwork'}.{ext}"
    folder = os.path.join(
        current_app.config["UPLOAD_FOLDER"], current_app.config["ARTWORK_UPLOAD_SUBDIR"]
    )
    return send_from_directory(folder, filename, as_attachment=True, download_name=download_name)
