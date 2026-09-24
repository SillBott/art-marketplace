import os
import uuid
from PIL import Image, ImageDraw, ImageFont
from flask import current_app
from werkzeug.utils import secure_filename


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def save_upload(file_storage, subdir):
    """Save an uploaded FileStorage under UPLOAD_FOLDER/subdir with a
    random-safe filename. Returns the stored filename (not full path)."""
    ext = file_storage.filename.rsplit(".", 1)[-1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    _ensure_dir(folder)
    file_storage.save(os.path.join(folder, filename))
    return filename


def make_watermarked_preview(original_filename, subdir, text="PREVIEW"):
    """Create a watermarked copy of an uploaded artwork image, used for
    public preview so the full-resolution file is only released after
    purchase. Returns the preview filename."""
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subdir)
    src_path = os.path.join(folder, original_filename)

    try:
        img = Image.open(src_path).convert("RGBA")
    except Exception:
        return original_filename  # fall back silently if not a real image

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font_size = max(20, img.width // 12)
        font = ImageFont.load_default(size=font_size)
    except Exception:
        font = ImageFont.load_default()

    # Tile the watermark text diagonally across the image
    step_x = max(img.width // 3, 150)
    step_y = max(img.height // 4, 100)
    for y in range(0, img.height + step_y, step_y):
        for x in range(0, img.width + step_x, step_x):
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 90))

    watermarked = Image.alpha_composite(img, overlay).convert("RGB")

    preview_name = f"preview_{original_filename.rsplit('.', 1)[0]}.jpg"
    watermarked.save(os.path.join(folder, preview_name), "JPEG", quality=85)
    return preview_name


def upload_url(subdir, filename):
    """Build the /uploads/... URL for a stored file (served by app.py)."""
    if not filename:
        return None
    return f"/uploads/{subdir}/{filename}"
