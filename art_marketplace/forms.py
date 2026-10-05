import re

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (
    StringField, PasswordField, TextAreaField, FloatField,
    SelectField, SubmitField,
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, Length, NumberRange, Optional,
    Regexp, ValidationError,
)

# ---------------------------------------------------------------- limits ---
# แก้ตัวเลขตรงนี้ที่เดียว ใช้ได้ทุกฟอร์ม
USERNAME_MIN, USERNAME_MAX = 3, 20
NAME_MAX = 120            # ชื่อที่แสดง / สถาบัน / ชื่อบัญชี PromptPay
TITLE_MAX = 100           # ชื่อผลงาน
TECHNIQUE_MAX = 100
DESCRIPTION_MAX = 1000    # รายละเอียดผลงาน
BIO_MAX = 500
COMMENT_MAX = 500         # รีวิว
PRICE_MIN, PRICE_MAX = 1, 100000   # บาท
SIZE_MIN, SIZE_MAX = 0.1, 500      # ซม.

# username: อังกฤษ ตัวเลข _ . - และตัวอักษรไทย (พยัญชนะ สระ วรรณยุกต์) เท่านั้น
# ใช้ whitelist จึงตัดอีโมจิ ช่องว่าง และสัญลักษณ์แปลก ๆ ออกหมด
USERNAME_RE = r"^[A-Za-z0-9_.\-\u0E01-\u0E3A\u0E40-\u0E4E]+$"

# ช่วงอีโมจิ/สัญลักษณ์ภาพ (Python re ไม่รองรับ \p{Emoji} จึงระบุช่วงเอง)
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"   # emoji หลัก, ธง, สัญลักษณ์ต่าง ๆ
    "\U00002600-\U000027BF"   # ☀ ★ ✂ ✅ ❤ ...
    "\U00002300-\U000023FF"   # ⌚ ⏰ ...
    "\U00002B00-\U00002BFF"   # ⭐ ⬆ ...
    "\U00002190-\U000021FF"   # ลูกศร
    "\U00002900-\U0000297F"
    "\U0000FE00-\U0000FE0F"   # variation selector
    "\U0000200D"              # zero-width joiner
    "\U000020E3"              # keycap
    "\U000000A9\U000000AE\U00002122\U00002139\U00003030\U0000303D"
    "]"
)


def has_emoji(text):
    return bool(text and _EMOJI_RE.search(text))


def no_emoji(form, field):
    if has_emoji(field.data):
        raise ValidationError("ห้ามใช้อีโมจิในช่องนี้")


def max_2_decimals(form, field):
    if field.data is not None and round(field.data, 2) != field.data:
        raise ValidationError("ทศนิยมได้ไม่เกิน 2 ตำแหน่ง")


def _strip(value):
    return value.strip() if isinstance(value, str) else value


# ฟิลด์ที่ใช้ซ้ำ
def username_validators():
    return [
        DataRequired(message="กรุณากรอกชื่อผู้ใช้"),
        Length(USERNAME_MIN, USERNAME_MAX,
               message=f"ชื่อผู้ใช้ต้องยาว {USERNAME_MIN}-{USERNAME_MAX} ตัวอักษร"),
        Regexp(USERNAME_RE,
               message="ใช้ได้เฉพาะ ก-ฮ, A-Z, 0-9, _ . - (ห้ามอีโมจิ ช่องว่าง และสัญลักษณ์พิเศษ)"),
    ]


class RegisterForm(FlaskForm):
    username = StringField("ชื่อผู้ใช้", filters=[_strip], validators=username_validators())
    email = StringField("อีเมล", filters=[_strip], validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("รหัสผ่าน", validators=[DataRequired(), Length(min=6, max=72)])
    confirm = PasswordField(
        "ยืนยันรหัสผ่าน",
        validators=[DataRequired(), EqualTo("password", message="รหัสผ่านไม่ตรงกัน")],
    )
    role = SelectField(
        "สมัครในฐานะ",
        choices=[("customer", "ลูกค้า (ซื้อผลงาน)"), ("artist", "ศิลปิน (ขายผลงาน)")],
    )
    display_name = StringField(
        "ชื่อที่แสดง (สำหรับศิลปิน)", filters=[_strip],
        validators=[Optional(), Length(max=NAME_MAX), no_emoji],
    )
    submit = SubmitField("สมัครสมาชิก")


class LoginForm(FlaskForm):
    # ไม่ใส่ validator เข้มที่นี่ เพื่อไม่ให้บัญชีเก่าล็อกอินไม่ได้
    username = StringField("ชื่อผู้ใช้หรืออีเมล", validators=[DataRequired(), Length(max=120)])
    password = PasswordField("รหัสผ่าน", validators=[DataRequired(), Length(max=72)])
    submit = SubmitField("เข้าสู่ระบบ")


class ArtworkForm(FlaskForm):
    title = StringField(
        "ชื่อผลงาน", filters=[_strip],
        validators=[DataRequired(), Length(max=TITLE_MAX), no_emoji],
    )
    description = TextAreaField(
        "รายละเอียด", filters=[_strip],
        validators=[Optional(), Length(max=DESCRIPTION_MAX)],
    )
    category_id = SelectField("หมวดหมู่", coerce=int, validators=[DataRequired()])
    technique = StringField(
        "เทคนิค", filters=[_strip],
        validators=[Optional(), Length(max=TECHNIQUE_MAX)],
    )
    width_cm = FloatField(
        "ความกว้าง (ซม.)",
        validators=[Optional(), NumberRange(SIZE_MIN, SIZE_MAX, message=f"ต้องอยู่ระหว่าง {SIZE_MIN}-{SIZE_MAX} ซม.")],
    )
    height_cm = FloatField(
        "ความสูง (ซม.)",
        validators=[Optional(), NumberRange(SIZE_MIN, SIZE_MAX, message=f"ต้องอยู่ระหว่าง {SIZE_MIN}-{SIZE_MAX} ซม.")],
    )
    price = FloatField(
        "ราคา (บาท)",
        validators=[
            DataRequired(message="กรุณากรอกราคา"),
            NumberRange(PRICE_MIN, PRICE_MAX,
                        message=f"ราคาต้องอยู่ระหว่าง {PRICE_MIN:,}-{PRICE_MAX:,} บาท"),
            max_2_decimals,
        ],
    )
    image = FileField(
        "รูปภาพผลงาน",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "รองรับเฉพาะไฟล์รูปภาพ")],
    )
    submit = SubmitField("บันทึก")


class CategoryForm(FlaskForm):
    name = StringField(
        "ชื่อหมวดหมู่", filters=[_strip],
        validators=[DataRequired(), Length(max=80), no_emoji],
    )
    submit = SubmitField("บันทึก")


class ArtistProfileForm(FlaskForm):
    display_name = StringField(
        "ชื่อที่แสดง", filters=[_strip],
        validators=[DataRequired(), Length(max=NAME_MAX), no_emoji],
    )
    school = StringField(
        "สถาบันการศึกษา", filters=[_strip],
        validators=[Optional(), Length(max=150), no_emoji],
    )
    bio = TextAreaField(
        "แนะนำตัว", filters=[_strip],
        validators=[Optional(), Length(max=BIO_MAX)],
    )
    promptpay_id = StringField(
        "หมายเลข PromptPay ของฉัน (เบอร์โทรหรือเลขบัตรประชาชน)", filters=[_strip],
        validators=[Optional(), Regexp(r"^[0-9\-]{9,20}$", message="กรอกเฉพาะตัวเลข (เบอร์โทร 10 หลัก หรือเลขบัตร 13 หลัก)")],
    )
    promptpay_name = StringField(
        "ชื่อบัญชีที่แสดงให้ลูกค้าเห็น", filters=[_strip],
        validators=[Optional(), Length(max=NAME_MAX), no_emoji],
    )
    qr_image = FileField(
        "รูป QR Code ของฉัน (ถ้ามี)",
        validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "รองรับเฉพาะไฟล์รูปภาพ")],
    )
    submit = SubmitField("บันทึกโปรไฟล์")


class AccountForm(FlaskForm):
    """Generic account-info edit, available to every logged-in user."""
    username = StringField("ชื่อผู้ใช้", filters=[_strip], validators=username_validators())
    email = StringField("อีเมล", filters=[_strip], validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField("บันทึก")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("รหัสผ่านปัจจุบัน", validators=[DataRequired()])
    new_password = PasswordField("รหัสผ่านใหม่", validators=[DataRequired(), Length(min=6, max=72)])
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
        "หมายเลข PromptPay (เบอร์โทรหรือเลขบัตรประชาชน)", filters=[_strip],
        validators=[Optional(), Regexp(r"^[0-9\-]{9,20}$", message="กรอกเฉพาะตัวเลข (เบอร์โทร 10 หลัก หรือเลขบัตร 13 หลัก)")],
    )
    promptpay_name = StringField(
        "ชื่อบัญชีที่แสดงให้ลูกค้าเห็น", filters=[_strip],
        validators=[Optional(), Length(max=NAME_MAX), no_emoji],
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
    comment = TextAreaField(
        "ความคิดเห็น", filters=[_strip],
        validators=[Optional(), Length(max=COMMENT_MAX)],
    )
    submit = SubmitField("บันทึกรีวิว")
