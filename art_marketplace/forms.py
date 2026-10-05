from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, TextAreaField, FloatField,
    SelectField, SubmitField,
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, NumberRange, Optional,
)

def ascii_only(form, field):
    if field.data and not field.data.isascii():
        raise ValidationError("อีเมลใช้ได้เฉพาะภาษาอังกฤษ ตัวเลข และสัญลักษณ์ปกติ (ห้ามอีโมจิ)")

class RegisterForm(FlaskForm):
    username = StringField("ชื่อผู้ใช้", validators=[DataRequired(), Length(3, 80)])
    email = StringField("อีเมล", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("รหัสผ่าน", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField(
        "ยืนยันรหัสผ่าน",
        validators=[DataRequired(), EqualTo("password", message="รหัสผ่านไม่ตรงกัน")],
    )
    role = SelectField(
        "สมัครในฐานะ",
        choices=[("customer", "ลูกค้า (ซื้อผลงาน)"), ("artist", "ศิลปิน (ขายผลงาน)")],
    )
    display_name = StringField("ชื่อที่แสดง (สำหรับศิลปิน)", validators=[Optional(), Length(max=120)])
    submit = SubmitField("สมัครสมาชิก")


class LoginForm(FlaskForm):
    username = StringField("ชื่อผู้ใช้หรืออีเมล", validators=[DataRequired()])
    password = PasswordField("รหัสผ่าน", validators=[DataRequired()])
    submit = SubmitField("เข้าสู่ระบบ")


class ArtworkForm(FlaskForm):
    title = StringField("ชื่อผลงาน", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("รายละเอียด", validators=[Optional()])
    category_id = SelectField("หมวดหมู่", coerce=int, validators=[DataRequired()])
    technique = StringField("เทคนิค", validators=[Optional(), Length(max=120)])
    width_cm = FloatField("ความกว้าง (ซม.)", validators=[Optional(), NumberRange(min=0.1)])
    height_cm = FloatField("ความสูง (ซม.)", validators=[Optional(), NumberRange(min=0.1)])
    price = FloatField("ราคา (บาท)", validators=[DataRequired(), NumberRange(min=1)])
    image = FileField(
        "รูปภาพผลงาน",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "รองรับเฉพาะไฟล์รูปภาพ")],
    )
    submit = SubmitField("บันทึก")


class CategoryForm(FlaskForm):
    name = StringField("ชื่อหมวดหมู่", validators=[DataRequired(), Length(max=80)])
    submit = SubmitField("บันทึก")


class ArtistProfileForm(FlaskForm):
    display_name = StringField("ชื่อที่แสดง", validators=[DataRequired(), Length(max=120)])
    school = StringField("สถาบันการศึกษา", validators=[Optional(), Length(max=150)])
    bio = TextAreaField("แนะนำตัว", validators=[Optional()])
    promptpay_id = StringField(
        "หมายเลข PromptPay ของฉัน (เบอร์โทรหรือเลขบัตรประชาชน)",
        validators=[Optional(), Length(max=50)],
    )
    promptpay_name = StringField(
        "ชื่อบัญชีที่แสดงให้ลูกค้าเห็น",
        validators=[Optional(), Length(max=120)],
    )
    qr_image = FileField(
        "รูป QR Code ของฉัน (ถ้ามี)",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "รองรับเฉพาะไฟล์รูปภาพ")],
    )
    submit = SubmitField("บันทึกโปรไฟล์")


class AccountForm(FlaskForm):
    """Generic account-info edit, available to every logged-in user."""
    username = StringField("ชื่อผู้ใช้", validators=[DataRequired(), Length(3, 80)])
    email = StringField("อีเมล", validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField("บันทึก")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("รหัสผ่านปัจจุบัน", validators=[DataRequired()])
    new_password = PasswordField("รหัสผ่านใหม่", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField(
        "ยืนยันรหัสผ่านใหม่",
        validators=[DataRequired(), EqualTo("new_password", message="รหัสผ่านไม่ตรงกัน")],
    )
    submit = SubmitField("เปลี่ยนรหัสผ่าน")


class CheckoutForm(FlaskForm):
    slip = FileField(
        "แนบสลิปการโอนเงิน",
        validators=[
            DataRequired(message="กรุณาแนบสลิป"),
            FileAllowed(["png", "jpg", "jpeg", "webp"], "รองรับเฉพาะไฟล์รูปภาพ"),
        ],
    )
    submit = SubmitField("ยืนยันการสั่งซื้อ")


class OrderStatusForm(FlaskForm):
    status = SelectField(
        "สถานะ",
        choices=[
            ("paid", "ชำระเงินแล้ว"),
            ("shipped", "จัดส่งแล้ว"),
            ("completed", "สำเร็จ"),
            ("cancelled", "ยกเลิก"),
        ],
    )
    submit = SubmitField("อัปเดตสถานะ")

class SiteSettingsForm(FlaskForm):
    promptpay_id = StringField(
        "หมายเลข PromptPay (เบอร์โทรหรือเลขบัตรประชาชน)",
        validators=[Optional(), Length(max=50)],
    )
    promptpay_name = StringField(
        "ชื่อบัญชีที่แสดงให้ลูกค้าเห็น",
        validators=[Optional(), Length(max=120)],
    )
    qr_image = FileField(
        "รูป QR Code (ถ้ามี)",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "รองรับเฉพาะไฟล์รูปภาพ")],
    )
    submit = SubmitField("บันทึกการตั้งค่า")

class DeleteAccountForm(FlaskForm):
    password = PasswordField("ยืนยันรหัสผ่านเพื่อลบบัญชี", validators=[DataRequired()])
    submit = SubmitField("ลบบัญชีถาวร")

class ReviewForm(FlaskForm):
    rating = SelectField(
        "ให้คะแนน",
        coerce=int,
        choices=[(5, "★★★★★ (5)"), (4, "★★★★ (4)"), (3, "★★★ (3)"), (2, "★★ (2)"), (1, "★ (1)")],
        validators=[DataRequired()],
    )
    comment = TextAreaField("ความคิดเห็น", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("บันทึกรีวิว")
