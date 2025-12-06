import io
import os
import re
import base64
from PIL import Image, ImageDraw, ImageFont, ImageOps
import streamlit as st

# Try import cairosvg (SVG -> PNG). If unavailable, we'll fallback to Pillow drawing.
try:
    import cairosvg
    CAIROSVG_AVAILABLE = True
except Exception:
    CAIROSVG_AVAILABLE = False

# ------------------------
# Configuration
# ------------------------

TEMPLATE_PATH = "assets/template.png"

SLOT_X = 330
SLOT_Y = 210
SLOT_W = 420
SLOT_H = 470

# Text boxes (x1, x2, y1, y2)
NAME_BOX = (285, 795, 705, 785)
DESG_BOX = (357, 722, 807, 855)

# Hindi + English font paths
NAME_FONT_EN = "assets/Poppins-SemiBold.ttf"
NAME_FONT_HI = "assets/NotoSansDevanagari-SemiBold.ttf"

DESG_FONT_EN = "assets/Poppins-Medium.ttf"
DESG_FONT_HI = "assets/NotoSansDevanagari-Medium.ttf"

# ------------------------
# Utilities
# ------------------------

def is_english_text(text):
    return re.fullmatch(r"[A-Za-z0-9 .,'’\-]+", text or "") is not None

def embed_font_base64(font_path):
    """
    Read ttf font and return a data:font/ttf;base64,... string to embed in SVG.
    """
    with open(font_path, "rb") as f:
        b = f.read()
    b64 = base64.b64encode(b).decode("ascii")
    return f"data:font/ttf;base64,{b64}"

def fit_image_to_frame(img, frame_w, frame_h):
    """
    Cover-fit (fill & center-crop) the image to exactly frame_w x frame_h
    """
    original_w, original_h = img.size
    img_ratio = original_w / original_h
    frame_ratio = frame_w / frame_h

    if img_ratio > frame_ratio:
        # image wider → match height
        new_height = frame_h
        new_width = int(new_height * img_ratio)
    else:
        # image taller → match width
        new_width = frame_w
        new_height = int(new_width / img_ratio)

    img = img.resize((new_width, new_height), Image.LANCZOS)
    left = (new_width - frame_w) // 2
    top = (new_height - frame_h) // 2
    right = left + frame_w
    bottom = top + frame_h
    return img.crop((left, top, right, bottom))

# ------------------------
# SVG text rendering helpers
# ------------------------

def estimate_font_size_pil(text, font_path, max_font_size, allowed_width, allowed_height, min_font_size=6):
    """
    Use PIL (approx) to find a font size that will likely fit inside allowed_width/height.
    Returns chosen font_size and measured (text_width, text_height) with PIL.
    This is an estimation step; actual shaping in SVG may be slightly different,
    but usually close enough when using the same TTF.
    """
    # Start with max size
    font_size = max_font_size
    font = ImageFont.truetype(font_path, font_size)
    # We'll use a temporary ImageDraw to measure
    temp_img = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(temp_img)
    bbox = draw.textbbox((0,0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    if text_width <= allowed_width and text_height <= allowed_height:
        return font_size, (text_width, text_height)

    # Compute scale factor
    width_scale = allowed_width / text_width if text_width>0 else 1.0
    height_scale = allowed_height / text_height if text_height>0 else 1.0
    scale = min(width_scale, height_scale)
    new_size = max(min_font_size, int(font_size * scale))

    # Iteratively ensure fit (safety)
    while new_size >= min_font_size:
        font = ImageFont.truetype(font_path, new_size)
        bbox = draw.textbbox((0,0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        if w <= allowed_width and h <= allowed_height:
            return new_size, (w,h)
        new_size -= 1

    # fallback:
    font = ImageFont.truetype(font_path, min_font_size)
    bbox = draw.textbbox((0,0), text, font=font)
    return min_font_size, (bbox[2]-bbox[0], bbox[3]-bbox[1])

def render_text_svg_to_image(text, font_path, font_size, fill, box_w, box_h):
    """
    Build an SVG (with embedded font), render to PNG bytes via cairosvg (if available),
    return a PIL.Image of size (box_w, box_h) with the rendered text centered.
    """
    font_data_url = embed_font_base64(font_path)
    # Use a simple font-family name
    font_family = "EmbeddedCustom"

    # Build SVG with embedded @font-face and centered text.
    # Using <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle">
    svg = f'''<?xml version="1.0" encoding="utf-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" width="{box_w}px" height="{box_h}px" viewBox="0 0 {box_w} {box_h}">
      <defs>
        <style type="text/css">
          @font-face {{
            font-family: '{font_family}';
            src: url('{font_data_url}') format('truetype');
          }}
          .t {{ font-family: '{font_family}'; font-size: {font_size}px; fill: {fill}; }}
        </style>
      </defs>
      <rect width="100%" height="100%" fill="none" />
      <text x="50%" y="50%" class="t" text-anchor="middle" dominant-baseline="middle">{text}</text>
    </svg>
    '''

    if not CAIROSVG_AVAILABLE:
        # Fallback path: render using Pillow (may break Devanagari shaping)
        temp = Image.new("RGBA", (box_w, box_h), (0,0,0,0))
        draw = ImageDraw.Draw(temp)
        font = ImageFont.truetype(font_path, font_size)
        bbox = draw.textbbox((0,0), text, font=font)
        text_w = bbox[2]-bbox[0]; text_h = bbox[3]-bbox[1]
        x = (box_w - text_w)//2
        y = (box_h - text_h)//2
        draw.text((x,y), text, font=font, fill=fill)
        return temp

    # Use cairosvg to convert SVG to PNG bytes and open with PIL
    png_bytes = cairosvg.svg2png(bytestring=svg.encode('utf-8'))
    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    return img

def paste_svg_text_box(base_image, text, font_path, max_font_size, box_x1, box_x2, box_y1, box_y2, text_color=(255,255,255)):
    """
    High-level: measure a font size that fits (using PIL estimate), render SVG with that font,
    and paste resulting PNG into base_image at box_x1,box_y1.
    """
    allowed_w = box_x2 - box_x1
    allowed_h = box_y2 - box_y1

    # Estimate a font size that fits using PIL (approx)
    chosen_size, (meas_w, meas_h) = estimate_font_size_pil(text, font_path, max_font_size, allowed_w, allowed_h)

    # Render SVG using chosen_size
    fill = f"rgb({text_color[0]},{text_color[1]},{text_color[2]})"
    rendered = render_text_svg_to_image(text, font_path, chosen_size, fill, allowed_w, allowed_h)

    # Paste rendered onto base image in the box
    base_image.paste(rendered, (box_x1, box_y1), rendered)
    return base_image

# ------------------------
# Streamlit UI
# ------------------------

st.set_page_config(page_title="GLF ID Card Generator", layout="centered")
st.title("GLF ID Card Generator")
st.write("Upload a photo and enter name & designation to generate an ID card.")

uploaded_file = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"])
name_text = st.text_input("Full Name")
designation_text = st.text_input("Designation")

if st.button("Generate ID Card"):

    if uploaded_file is None:
        st.error("Please upload a photo.")
    elif not name_text.strip():
        st.error("Please enter a name.")
    elif not designation_text.strip():
        st.error("Please enter a designation.")
    else:
        if not os.path.exists(TEMPLATE_PATH):
            st.error(f"ID card template not found: {TEMPLATE_PATH}")
        else:
            # Load template
            id_card = Image.open(TEMPLATE_PATH).convert("RGBA")

            # Load uploaded photo and correct EXIF orientation
            person_img = Image.open(uploaded_file)
            person_img = ImageOps.exif_transpose(person_img)
            person_img = person_img.convert("RGBA")

            # Fit image into frame and paste
            fitted_img = fit_image_to_frame(person_img, SLOT_W, SLOT_H)
            background = Image.new("RGBA", id_card.size, (0,0,0,0))
            background.paste(fitted_img, (SLOT_X, SLOT_Y))

            final = Image.alpha_composite(background, id_card)

            # Select fonts based on language
            name_font_path = NAME_FONT_EN if is_english_text(name_text) else NAME_FONT_HI
            desg_font_path = DESG_FONT_EN if is_english_text(designation_text) else DESG_FONT_HI

            # Render name using SVG -> PNG and paste
            final = paste_svg_text_box(
                final,
                text=name_text,
                font_path=name_font_path,
                max_font_size=56,
                box_x1=NAME_BOX[0],
                box_x2=NAME_BOX[1],
                box_y1=NAME_BOX[2],
                box_y2=NAME_BOX[3],
                text_color=(255,255,255)
            )

            # Render designation using SVG -> PNG and paste
            final = paste_svg_text_box(
                final,
                text=designation_text,
                font_path=desg_font_path,
                max_font_size=30,
                box_x1=DESG_BOX[0],
                box_x2=DESG_BOX[1],
                box_y1=DESG_BOX[2],
                box_y2=DESG_BOX[3],
                text_color=(0,0,0)
            )

            # Preview and download
            st.image(final, caption="Generated ID Card", width=550)

            img_bytes = io.BytesIO()
            final.save(img_bytes, format="PNG")
            img_bytes.seek(0)

            st.download_button("Download ID Card", img_bytes, file_name="final_id_card.png", mime="image/png")

            if not CAIROSVG_AVAILABLE:
                st.warning("Note: cairosvg is not installed — rendered text used Pillow fallback which may not shape Devanagari correctly. Install cairosvg and system Cairo/Pango to enable proper shaping.")
