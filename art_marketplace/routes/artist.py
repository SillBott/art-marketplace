from flask import Blueprint, render_template, redirect, url_for, flash, abort, current_app
from flask_login import login_required, current_user

from extensions import db
from models import Artwork, Category, AuditLog
from forms import ArtworkForm, ArtistProfileForm
from decorators import artist_required
from utils import save_upload, save_artwork_image

bp = Blueprint("artist", __name__, url_prefix="/artist")


@bp.route("/profile", methods=["GET", "POST"])
@login_required
@artist_required
def profile():
    profile = current_user.artist_profile
    form = ArtistProfileForm(obj=profile)
    if form.validate_on_submit():
        profile.display_name = form.display_name.data
        profile.school = form.school.data
        profile.bio = form.bio.data
        profile.promptpay_id = form.promptpay_id.data
        profile.promptpay_name = form.promptpay_name.data
        if form.qr_image.data:
            filename = save_upload(form.qr_image.data, current_app.config["SETTINGS_UPLOAD_SUBDIR"])
            profile.qr_filename = filename
        AuditLog.record(current_user.id, "update", "artist_profiles", profile.id)
        db.session.commit()
        flash("บันทึกโปรไฟล์แล้ว", "success")
        return redirect(url_for("artist.profile"))
    return render_template("artist_profile.html", form=form, profile=profile)


@bp.route("/artworks")
@login_required
@artist_required
def my_artworks():
    artworks = (
        Artwork.query.filter_by(artist_id=current_user.artist_profile.id)
        .order_by(Artwork.created_at.desc())
        .all()
    )
    return render_template("my_artworks.html", artworks=artworks)


def _artwork_form_choices(form):
    form.category_id.choices = [(c.id, c.name) for c in Category.query.order_by(Category.name)]


@bp.route("/artworks/new", methods=["GET", "POST"])
@login_required
@artist_required
def new_artwork():
    form = ArtworkForm()
    _artwork_form_choices(form)

    if form.validate_on_submit():
        artwork = Artwork(
            artist_id=current_user.artist_profile.id,
            category_id=form.category_id.data,
            title=form.title.data,
            description=form.description.data,
            technique=form.technique.data,
            size=form.size.data,
            price=form.price.data,
            approved=False,
        )
        if form.image.data:
            subdir = current_app.config["ARTWORK_UPLOAD_SUBDIR"]
            artwork.image_filename, artwork.preview_filename = save_artwork_image(form.image.data, subdir)

        db.session.add(artwork)
        db.session.flush()
        AuditLog.record(current_user.id, "create", "artworks", artwork.id, artwork.title)
        db.session.commit()
        flash("ส่งผลงานแล้ว รอแอดมินตรวจสอบก่อนเผยแพร่", "success")
        return redirect(url_for("artist.my_artworks"))

    return render_template("upload_artwork.html", form=form, mode="new")


@bp.route("/artworks/<int:artwork_id>/edit", methods=["GET", "POST"])
@login_required
@artist_required
def edit_artwork(artwork_id):
    artwork = Artwork.query.get_or_404(artwork_id)
    if artwork.artist_id != current_user.artist_profile.id and not current_user.is_staff:
        abort(403)

    form = ArtworkForm(obj=artwork)
    _artwork_form_choices(form)

    if form.validate_on_submit():
        artwork.title = form.title.data
        artwork.description = form.description.data
        artwork.category_id = form.category_id.data
        artwork.technique = form.technique.data
        artwork.size = form.size.data
        artwork.price = form.price.data

        if form.image.data:
            subdir = current_app.config["ARTWORK_UPLOAD_SUBDIR"]
            artwork.image_filename, artwork.preview_filename = save_artwork_image(form.image.data, subdir)

        AuditLog.record(current_user.id, "update", "artworks", artwork.id, artwork.title)
        db.session.commit()
        flash("แก้ไขผลงานแล้ว", "success")
        return redirect(url_for("artist.my_artworks"))

    return render_template("upload_artwork.html", form=form, mode="edit", artwork=artwork)


@bp.route("/artworks/<int:artwork_id>/delete", methods=["POST"])
@login_required
@artist_required
def delete_artwork(artwork_id):
    artwork = Artwork.query.get_or_404(artwork_id)
    if artwork.artist_id != current_user.artist_profile.id and not current_user.is_staff:
        abort(403)

    AuditLog.record(current_user.id, "delete", "artworks", artwork.id, artwork.title)
    db.session.delete(artwork)
    db.session.commit()
    flash("ลบผลงานแล้ว", "info")
    return redirect(url_for("artist.my_artworks"))
