import io
import os
import re
from PIL import Image, ImageDraw, ImageFont, ImageOps
import streamlit as st


# Configuration

TEMPLATE_PATH = "assets/template.png"

STANDARD_W = 500
STANDARD_H = 750

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

# Utility functions

def is_english_text(text):
    return re.fullmatch(r"[A-Za-z0-9 .,'’\-]+", text or "") is not None

# Image Processing Function

def fit_image_to_frame(img, frame_w, frame_h):
    """
    Resizes the image to fill the frame completely (cover fit)
    while keeping aspect ratio. Crops excess from center.
    """
    original_w, original_h = img.size
    img_ratio = original_w / original_h
    frame_ratio = frame_w / frame_h

    # If image is wider → match height, crop sides
    if img_ratio > frame_ratio:
        new_height = frame_h
        new_width = int(new_height * img_ratio)
    else:
        # If image is taller → match width, crop top/bottom
        new_width = frame_w
        new_height = int(new_width / img_ratio)

    # Resize image
    img = img.resize((new_width, new_height), Image.LANCZOS)

    # Center crop
    left = (new_width - frame_w) // 2
    top = (new_height - frame_h) // 2
    right = left + frame_w
    bottom = top + frame_h

    return img.crop((left, top, right, bottom))


# Text Processing Function

def add_text_fit_centered(
    base_image,
    text,
    font_path,
    max_font_size,
    box_x1,
    box_x2,
    box_y1,
    box_y2,
    min_font_size=10,
    text_color=(255, 255, 255)
):
    draw = ImageDraw.Draw(base_image)

    allowed_width = box_x2 - box_x1
    allowed_height = box_y2 - box_y1

    # Start with max font size
    font_size = max_font_size
    font = ImageFont.truetype(font_path, font_size)

    # Get natural text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Scale down if needed
    if text_width > allowed_width or text_height > allowed_height:
        width_scale = allowed_width / text_width
        height_scale = allowed_height / text_height
        scale = min(width_scale, height_scale)
        
        font_size = max(min_font_size, int(font_size * scale))
        font = ImageFont.truetype(font_path, font_size)
        
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

    # Horizontal centering
    x = box_x1 + (allowed_width - text_width) // 2

    # Vertical centering (bbox-based)
    y = box_y1 + (allowed_height - text_height) // 2

    # Language-Based Correction
    if is_english_text(text):
        y -= 10   # English slightly raised

    draw.text((x, y), text, font=font, fill=text_color)
    return base_image


# Streamlit UI

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
            # Load ID card template
            id_card = Image.open(TEMPLATE_PATH).convert("RGBA")

            # Load uploaded photo
            person_img = Image.open(uploaded_file).convert("RGBA")

            # Auto-correct orientation using EXIF
            person_img = ImageOps.exif_transpose(person_img)

            person_img = person_img.convert("RGBA")

            # Fit image exactly into the frame (cover fit)
            fitted_img = fit_image_to_frame(person_img, SLOT_W, SLOT_H)

            # Place in background
            background = Image.new("RGBA", id_card.size, (0, 0, 0, 0))
            background.paste(fitted_img, (SLOT_X, SLOT_Y))

            # Merge with ID Card template
            final = Image.alpha_composite(background, id_card)

            # Select fonts based on language
            name_font = NAME_FONT_EN if is_english_text(name_text) else NAME_FONT_HI
            desg_font = DESG_FONT_EN if is_english_text(designation_text) else DESG_FONT_HI

            # Add Name
            final = add_text_fit_centered(
                final,
                text=name_text,
                font_path = name_font,
                max_font_size=56,
                box_x1=NAME_BOX[0],
                box_x2=NAME_BOX[1],
                box_y1=NAME_BOX[2],
                box_y2=NAME_BOX[3],
                text_color=(255, 255, 255)
            )

            # Add Designation
            final = add_text_fit_centered(
                final,
                text=designation_text,
                font_path = desg_font,
                max_font_size=30,
                box_x1=DESG_BOX[0],
                box_x2=DESG_BOX[1],
                box_y1=DESG_BOX[2],
                box_y2=DESG_BOX[3],
                text_color=(0, 0, 0)
            )

            # Display Preview
            st.image(final, caption="Generated ID Card", width=550)

            # Download Button
            img_bytes = io.BytesIO()
            final.save(img_bytes, format="PNG")
            img_bytes.seek(0)

            st.download_button(
                label="Download ID Card",
                data=img_bytes,
                file_name="final_id_card.png",
                mime="image/png"
            )
