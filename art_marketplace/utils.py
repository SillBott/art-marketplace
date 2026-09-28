import io
import os
import uuid
from PIL import Image, ImageDraw, ImageFont
from flask import current_app

try:
    import cloudinary
    import cloudinary.uploader
except ImportError:  # only required when CLOUDINARY_URL is actually set
    cloudinary = None


def _using_cloudinary():
    """True when a CLOUDINARY_URL env var is configured — Cloudinary's
    SDK auto-reads that var, no extra config code needed on our side."""
    return bool(os.environ.get("CLOUDINARY_URL")) and cloudinary is not None


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def _local_folder(subdir):
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    _ensure_dir(folder)
    return folder


def save_upload(file_storage, subdir):
    """Save an uploaded file. Uses Cloudinary (persistent) when
    CLOUDINARY_URL is configured; otherwise falls back to local disk —
    fine for local dev, but NOT persistent on Vercel (its filesystem is
    wiped between cold starts)."""
    if _using_cloudinary():
        result = cloudinary.uploader.upload(
            file_storage, folder=f"art_marketplace/{subdir}", resource_type="image",
        )
        return result["secure_url"]

    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = _local_folder(subdir)
    file_storage.save(os.path.join(folder, filename))
    return filename


def _add_watermark(image_bytes, text="PREVIEW"):
    """Return a BytesIO of a JPEG watermarked copy of the given image bytes."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font_size = max(20, img.width // 12)
        font = ImageFont.load_default(size=font_size)
    except Exception:
        font = ImageFont.load_default()

    step_x = max(img.width // 3, 150)
    step_y = max(img.height // 4, 100)
    for y in range(0, img.height + step_y, step_y):
        for x in range(0, img.width + step_x, step_x):
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 90))

    watermarked = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    watermarked.save(buf, "JPEG", quality=85)
    buf.seek(0)
    return buf


def save_artwork_image(file_storage, subdir):
    """Upload an artwork's original image AND a watermarked preview.
    Returns (image_ref, preview_ref) — Cloudinary URLs when configured,
    otherwise local filenames."""
    original_bytes = file_storage.read()
    file_storage.seek(0)  # rewind so it can still be saved/uploaded below

    try:
        watermark_buf = _add_watermark(original_bytes)
    except Exception:
        watermark_buf = None  # not a real image / Pillow couldn't open it

    if _using_cloudinary():
        original_result = cloudinary.uploader.upload(
            file_storage, folder=f"art_marketplace/{subdir}", resource_type="image",
        )
        image_ref = original_result["secure_url"]

        if watermark_buf is not None:
            preview_result = cloudinary.uploader.upload(
                watermark_buf, folder=f"art_marketplace/{subdir}", resource_type="image",
            )
            preview_ref = preview_result["secure_url"]
        else:
            preview_ref = image_ref
        return image_ref, preview_ref

    # Local disk fallback (dev only — not persistent on Vercel)
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = _local_folder(subdir)
    file_storage.save(os.path.join(folder, filename))

    if watermark_buf is not None:
        preview_name = f"preview_{filename.rsplit('.', 1)[0]}.jpg"
        with open(os.path.join(folder, preview_name), "wb") as f:
            f.write(watermark_buf.read())
    else:
        preview_name = filename
    return filename, preview_name


def upload_url(subdir, filename):
    """Build the URL for a stored file. Cloudinary refs are already full
    URLs and pass straight through; local filenames get the /uploads/...
    route (served by app.py) built for them."""
    if not filename:
        return None
    if filename.startswith("http://") or filename.startswith("https://"):
        return filename
    return f"/uploads/{subdir}/{filename}"
