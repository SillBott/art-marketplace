from flask import Blueprint, render_template, redirect, url_for, flash, session

from models import Artwork

bp = Blueprint("cart", __name__, url_prefix="/cart")

CART_KEY = "cart_artwork_ids"


def _get_cart_ids():
    return session.get(CART_KEY, [])


@bp.route("/")
def view():
    ids = _get_cart_ids()
    artworks = Artwork.query.filter(Artwork.id.in_(ids)).all() if ids else []
    # Preserve cart order, drop anything sold since it was added
    by_id = {a.id: a for a in artworks}
    items = [by_id[i] for i in ids if i in by_id and by_id[i].status == "available"]
    total = sum(a.price for a in items)
    return render_template("cart.html", items=items, total=total)


@bp.route("/add/<int:artwork_id>", methods=["POST"])
def add(artwork_id):
    artwork = Artwork.query.get_or_404(artwork_id)
    if artwork.status != "available" or not artwork.approved:
        flash("ผลงานนี้ไม่พร้อมจำหน่าย", "warning")
        return redirect(url_for("gallery.detail", artwork_id=artwork_id))

    ids = _get_cart_ids()
    if artwork_id not in ids:
        ids.append(artwork_id)
        session[CART_KEY] = ids
        flash("เพิ่มลงตะกร้าแล้ว", "success")
    else:
        flash("ผลงานนี้อยู่ในตะกร้าอยู่แล้ว", "info")
    return redirect(url_for("cart.view"))


@bp.route("/remove/<int:artwork_id>", methods=["POST"])
def remove(artwork_id):
    ids = _get_cart_ids()
    if artwork_id in ids:
        ids.remove(artwork_id)
        session[CART_KEY] = ids
    return redirect(url_for("cart.view"))
