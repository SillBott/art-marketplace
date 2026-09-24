from flask import Blueprint, render_template, request, current_app
from sqlalchemy import or_

from models import Artwork, Category
from utils import upload_url

bp = Blueprint("gallery", __name__)


@bp.app_template_filter("art_url")
def art_url_filter(filename):
    return upload_url(current_app.config["ARTWORK_UPLOAD_SUBDIR"], filename)


@bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    sort = request.args.get("sort", "newest")
    page = request.args.get("page", 1, type=int)

    query = Artwork.query.filter_by(approved=True)

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Artwork.title.ilike(like), Artwork.description.ilike(like))
        )
    if category_id:
        query = query.filter_by(category_id=category_id)

    if sort == "price_asc":
        query = query.order_by(Artwork.price.asc())
    elif sort == "price_desc":
        query = query.order_by(Artwork.price.desc())
    elif sort == "oldest":
        query = query.order_by(Artwork.created_at.asc())
    else:
        query = query.order_by(Artwork.created_at.desc())

    pagination = query.paginate(
        page=page, per_page=current_app.config["ITEMS_PER_PAGE"], error_out=False
    )

    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "index.html",
        artworks=pagination.items,
        pagination=pagination,
        categories=categories,
        q=q, category_id=category_id, sort=sort,
    )


@bp.route("/artwork/<int:artwork_id>")
def detail(artwork_id):
    artwork = Artwork.query.get_or_404(artwork_id)
    related = (
        Artwork.query.filter(
            Artwork.category_id == artwork.category_id,
            Artwork.id != artwork.id,
            Artwork.approved == True,  # noqa: E712
        )
        .limit(4)
        .all()
    )
    return render_template("artwork_detail.html", artwork=artwork, related=related)
