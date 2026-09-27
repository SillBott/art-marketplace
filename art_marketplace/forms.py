from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, TextAreaField, FloatField,
    SelectField, SubmitField,
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, NumberRange, Optional,
)


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
    size = StringField("ขนาด", validators=[Optional(), Length(max=60)])
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
    submit = SubmitField("บันทึกโปรไฟล์")


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
