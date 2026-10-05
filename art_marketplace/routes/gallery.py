import math
from flask import Blueprint, render_template, request, current_app, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_, func

from extensions import db
from models import Artwork, Category, ArtistProfile, Review, Like, Follow
from forms import ReviewForm
from utils import upload_url

bp = Blueprint("gallery", __name__)


@bp.app_template_filter("art_url")
def art_url_filter(filename):
    return upload_url(current_app.config["ARTWORK_UPLOAD_SUBDIR"], filename)


@bp.route("/")
def index():
    q = request.args.get("q", "").strip()[:100]          # จำกัดคำค้นหา 100 ตัวอักษร
    category_id = request.args.get("category", type=int)
    artist_id = request.args.get("artist", type=int)
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort = request.args.get("sort", "newest")
    page = request.args.get("page", 1, type=int)

    # กันค่า nan / inf / ตัวเลขใหญ่เกินจริง
    if min_price is not None and not (math.isfinite(min_price) and 0 <= min_price <= 1_000_000):
        min_price = None
    if max_price is not None and not (math.isfinite(max_price) and 0 <= max_price <= 1_000_000):
        max_price = None

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

    like_count = Like.query.filter_by(artwork_id=artwork.id).count()
    user_has_liked = (
        current_user.is_authenticated
        and Like.query.filter_by(artwork_id=artwork.id, user_id=current_user.id).first() is not None
    )

    reviews = (
        Review.query.filter_by(artwork_id=artwork.id)
        .order_by(Review.created_at.desc())
        .all()
    )
    avg_rating = db.session.query(func.avg(Review.rating)).filter(
        Review.artwork_id == artwork.id
    ).scalar()

    review_form = ReviewForm()
    user_review = None
    if current_user.is_authenticated:
        user_review = Review.query.filter_by(
            artwork_id=artwork.id, user_id=current_user.id
        ).first()
        if user_review and request.method == "GET":
            review_form.rating.data = user_review.rating
            review_form.comment.data = user_review.comment

    is_following = (
        current_user.is_authenticated
        and Follow.query.filter_by(
            follower_id=current_user.id, artist_id=artwork.artist_id
        ).first() is not None
    )

    return render_template(
        "artwork_detail.html", artwork=artwork, related=related,
        like_count=like_count, user_has_liked=user_has_liked,
        reviews=reviews, avg_rating=avg_rating,
        review_form=review_form, user_review=user_review,
        is_following=is_following,
    )


@bp.route("/artwork/<int:artwork_id>/like", methods=["POST"])
@login_required
def like(artwork_id):
    artwork = Artwork.query.get_or_404(artwork_id)
    existing = Like.query.filter_by(artwork_id=artwork.id, user_id=current_user.id).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(Like(artwork_id=artwork.id, user_id=current_user.id))
    db.session.commit()
    return redirect(url_for("gallery.detail", artwork_id=artwork_id))


@bp.route("/artwork/<int:artwork_id>/review", methods=["POST"])
@login_required
def review(artwork_id):
    artwork = Artwork.query.get_or_404(artwork_id)
    form = ReviewForm()
    if form.validate_on_submit():
        existing = Review.query.filter_by(
            artwork_id=artwork.id, user_id=current_user.id
        ).first()
        if existing:
            existing.rating = form.rating.data
            existing.comment = form.comment.data
        else:
            db.session.add(Review(
                artwork_id=artwork.id, user_id=current_user.id,
                rating=form.rating.data, comment=form.comment.data,
            ))
        db.session.commit()
        flash("บันทึกรีวิวแล้ว", "success")
    else:
        flash("กรุณาให้คะแนน 1-5 ดาว", "danger")
    return redirect(url_for("gallery.detail", artwork_id=artwork_id))


@bp.route("/artist/<int:artist_id>")
def artist_public_profile(artist_id):
    artist = ArtistProfile.query.get_or_404(artist_id)
    artworks = (
        Artwork.query.filter_by(artist_id=artist.id, approved=True)
        .order_by(Artwork.created_at.desc())
        .all()
    )
    follower_count = Follow.query.filter_by(artist_id=artist.id).count()
    is_following = (
        current_user.is_authenticated
        and Follow.query.filter_by(
            follower_id=current_user.id, artist_id=artist.id
        ).first() is not None
    )
    return render_template(
        "public_artist_profile.html", artist=artist, artworks=artworks,
        follower_count=follower_count, is_following=is_following,
    )


@bp.route("/artist/<int:artist_id>/follow", methods=["POST"])
@login_required
def follow_artist(artist_id):
    artist = ArtistProfile.query.get_or_404(artist_id)
    if artist.user_id == current_user.id:
        flash("ไม่สามารถติดตามตัวเองได้", "warning")
        return redirect(url_for("gallery.artist_public_profile", artist_id=artist_id))

    existing = Follow.query.filter_by(
        follower_id=current_user.id, artist_id=artist.id
    ).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(Follow(follower_id=current_user.id, artist_id=artist.id))
    db.session.commit()
    return redirect(url_for("gallery.artist_public_profile", artist_id=artist_id))

