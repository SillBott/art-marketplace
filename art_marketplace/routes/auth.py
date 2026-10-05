from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User, ArtistProfile, AuditLog, Order, OrderItem, Review, Like, Follow
from forms import RegisterForm, LoginForm, AccountForm, ChangePasswordForm, DeleteAccountForm

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _can_delete_account(user):
    """A user can't self-delete once there's real transaction history tied
    to them — deleting would break order records for themselves or buyers
    of their artworks. They can still contact an admin in that case."""
    if Order.query.filter_by(customer_id=user.id).first():
        return False, "คุณมีประวัติการสั่งซื้อ ไม่สามารถลบบัญชีได้ด้วยตัวเอง กรุณาติดต่อแอดมิน"

    if user.artist_profile:
        artwork_ids = [a.id for a in user.artist_profile.artworks]
        if artwork_ids and OrderItem.query.filter(OrderItem.artwork_id.in_(artwork_ids)).first():
            return False, "ผลงานของคุณมีประวัติการสั่งซื้อ ไม่สามารถลบบัญชีได้ด้วยตัวเอง กรุณาติดต่อแอดมิน"

    return True, None


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("gallery.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first():
            flash("มีชื่อผู้ใช้หรืออีเมลนี้ในระบบแล้ว", "danger")
            return render_template("register.html", form=form)

        user = User(username=form.username.data, email=form.email.data, role="customer")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        if form.role.data == "artist":
            display_name = form.display_name.data or form.username.data
            profile = ArtistProfile(user_id=user.id, display_name=display_name)
            db.session.add(profile)

        AuditLog.record(user.id, "create", "users", user.id, "self-registration")
        db.session.commit()

        flash("สมัครสมาชิกสำเร็จ กรุณาเข้าสู่ระบบ", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("gallery.index"))

    form = LoginForm()
    if form.validate_on_submit():
        ident = form.username.data.strip()
        user = User.query.filter(
            (User.username == ident) | (User.email == ident)
        ).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f"ยินดีต้อนรับ {user.username}", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("gallery.index"))
        flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "danger")

    return render_template("login.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("ออกจากระบบแล้ว", "info")
    return redirect(url_for("gallery.index"))


@bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    """Generic account-info page, available to every logged-in user
    regardless of role (username/email + password change)."""
    account_form = AccountForm(obj=current_user, prefix="account")
    password_form = ChangePasswordForm(prefix="password")
    delete_form = DeleteAccountForm(prefix="delete")

    if account_form.validate_on_submit():
        conflict = User.query.filter(
            User.id != current_user.id,
            (User.username == account_form.username.data)
            | (User.email == account_form.email.data),
        ).first()
        if conflict:
            flash("มีชื่อผู้ใช้หรืออีเมลนี้ถูกใช้แล้ว", "danger")
        else:
            current_user.username = account_form.username.data
            current_user.email = account_form.email.data
            AuditLog.record(current_user.id, "update", "users", current_user.id, "updated account info")
            db.session.commit()
            flash("บันทึกข้อมูลบัญชีแล้ว", "success")
        return redirect(url_for("auth.account"))

    if password_form.validate_on_submit():
        if not current_user.check_password(password_form.current_password.data):
            flash("รหัสผ่านปัจจุบันไม่ถูกต้อง", "danger")
        else:
            current_user.set_password(password_form.new_password.data)
            AuditLog.record(current_user.id, "update", "users", current_user.id, "changed password")
            db.session.commit()
            flash("เปลี่ยนรหัสผ่านแล้ว", "success")
        return redirect(url_for("auth.account"))

    return render_template(
        "account.html", account_form=account_form,
        password_form=password_form, delete_form=delete_form,
    )


@bp.route("/account/delete", methods=["POST"])
@login_required
def delete_account():
    form = DeleteAccountForm(prefix="delete")
    if not form.validate_on_submit():
        flash("กรุณากรอกรหัสผ่านให้ถูกต้อง", "danger")
        return redirect(url_for("auth.account"))

    if not current_user.check_password(form.password.data):
        flash("รหัสผ่านไม่ถูกต้อง", "danger")
        return redirect(url_for("auth.account"))

    ok, reason = _can_delete_account(current_user)
    if not ok:
        flash(reason, "danger")
        return redirect(url_for("auth.account"))

    if current_user.is_admin:
        other_admins = User.query.filter(
            User.role == "admin", User.id != current_user.id
        ).count()
        if other_admins == 0:
            flash("ไม่สามารถลบได้ เนื่องจากเป็นแอดมินคนสุดท้ายของระบบ", "danger")
            return redirect(url_for("auth.account"))

    user_id = current_user.id
    artist_profile = current_user.artist_profile

    if artist_profile:
        artwork_ids = [a.id for a in artist_profile.artworks]
        if artwork_ids:
            Review.query.filter(Review.artwork_id.in_(artwork_ids)).delete(synchronize_session=False)
            Like.query.filter(Like.artwork_id.in_(artwork_ids)).delete(synchronize_session=False)
        Follow.query.filter_by(artist_id=artist_profile.id).delete(synchronize_session=False)

    AuditLog.query.filter_by(user_id=user_id).update({"user_id": None})
    Order.query.filter_by(confirmed_by_id=user_id).update({"confirmed_by_id": None})
    Review.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    Like.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    Follow.query.filter_by(follower_id=user_id).delete(synchronize_session=False)

    user = User.query.get(user_id)
    logout_user()
    db.session.delete(user)
    db.session.commit()

    flash("ลบบัญชีของคุณเรียบร้อยแล้ว", "info")
    return redirect(url_for("gallery.index"))
