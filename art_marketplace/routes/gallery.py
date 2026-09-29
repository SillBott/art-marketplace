from flask import Blueprint, render_template, request, current_app
from sqlalchemy import or_

from models import Artwork, Category, ArtistProfile
from utils import upload_url

bp = Blueprint("gallery", __name__)


@bp.app_template_filter("art_url")
def art_url_filter(filename):
    return upload_url(current_app.config["ARTWORK_UPLOAD_SUBDIR"], filename)


@bp.route("/")
def index():
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    artist_id = request.args.get("artist", type=int)
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
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
    if artist_id:
        query = query.filter_by(artist_id=artist_id)
    if min_price is not None:
        query = query.filter(Artwork.price >= min_price)
    if max_price is not None:
        query = query.filter(Artwork.price <= max_price)

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
    artists = ArtistProfile.query.order_by(ArtistProfile.display_name).all()

    return render_template(
        "index.html",
        artworks=pagination.items,
        pagination=pagination,
        categories=categories, artists=artists,
        q=q, category_id=category_id, artist_id=artist_id,
        min_price=min_price, max_price=max_price, sort=sort,
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
