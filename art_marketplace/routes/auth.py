from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User, ArtistProfile, AuditLog
from forms import RegisterForm, LoginForm, AccountForm, ChangePasswordForm

bp = Blueprint("auth", __name__, url_prefix="/auth")


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

        # Everyone registers with the base "customer" role; picking
        # "artist" just also creates an ArtistProfile so they can sell.
        # Promotion to staff/admin is done later by an admin.
        user = User(username=form.username.data, email=form.email.data, role="customer")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # get user.id before commit

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
