import io
import os
from PIL import Image, ImageDraw, ImageFont
import streamlit as st


# Configuration

BANNER_PATH = "assets/template.png"

STANDARD_W = 500
STANDARD_H = 750

SLOT_X = 245
SLOT_Y = 85
SLOT_W = 600
SLOT_H = 800

# Text boxes (x1, x2, y1, y2)
NAME_BOX = (285, 795, 705, 785)
DESG_BOX = (357, 722, 807, 855)

NAME_FONT_PATH = "assets/Poppins-SemiBold.ttf"
DESG_FONT_PATH = "assets/Poppins-Medium.ttf"


# Image Processing Functions

def resize_input_image(img):
    img.thumbnail((STANDARD_W, STANDARD_H), Image.LANCZOS)
    background = Image.new("RGBA", (STANDARD_W, STANDARD_H), (0, 0, 0, 0))
    x = (STANDARD_W - img.width) // 2
    y = (STANDARD_H - img.height) // 2
    background.paste(img, (x, y))
    return background

def fit_image_to_slot(img, slot_w, slot_h):
    img_ratio = img.width / img.height
    slot_ratio = slot_w / slot_h

    if img_ratio > slot_ratio:
        new_height = slot_h
        new_width = int(img_ratio * new_height)
    else:
        new_width = slot_w
        new_height = int(new_width / img_ratio)

    img = img.resize((new_width, new_height), Image.LANCZOS)

    left = (new_width - slot_w) // 2
    top = (new_height - slot_h) // 2
    right = left + slot_w
    bottom = top + slot_h

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

    # If text exceeds width or height, scale down
    if text_width > allowed_width or text_height > allowed_height:
        width_scale = allowed_width / text_width
        height_scale = allowed_height / text_height
        scale = min(width_scale, height_scale)

        font_size = max(min_font_size, int(font_size * scale))
        font = ImageFont.truetype(font_path, font_size)

        # Recompute with final font size
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

    # Horizontal center inside the box
    x = box_x1 + (allowed_width - text_width) // 2

    # Vertical center inside the box
    y = box_y1 + (allowed_height - text_height) // 2

    draw.text((x, y), text, font=font, fill=text_color)
    return base_image


# Streamlit UI

st.set_page_config(page_title="GLF Banner Generator", layout="centered")
st.title("GLF Banner Generator")
st.write("Upload a photo and enter Name & Designation to generate a banner.")

uploaded_file = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"])
name_text = st.text_input("Full Name")
designation_text = st.text_input("Designation")

if st.button("Generate Banner"):

    if uploaded_file is None:
        st.error("Please upload a photo.")
    elif not name_text.strip():
        st.error("Please enter a name.")
    elif not designation_text.strip():
        st.error("Please enter a designation.")
    else:
        if not os.path.exists(BANNER_PATH):
            st.error(f"Banner template not found: {BANNER_PATH}")
        else:
            # Load banner
            banner = Image.open(BANNER_PATH).convert("RGBA")

            # Load uploaded photo
            person_img = Image.open(uploaded_file).convert("RGBA")

            # Standardize & fit person image
            person_img = resize_input_image(person_img)
            fitted_img = fit_image_to_slot(person_img, SLOT_W, SLOT_H)

            # Place in background
            background = Image.new("RGBA", banner.size, (0, 0, 0, 0))
            background.paste(fitted_img, (SLOT_X, SLOT_Y))

            # Merge with banner
            final = Image.alpha_composite(background, banner)

            # Add NAME (auto-fit)
            final = add_text_fit_centered(
                final,
                text=name_text,
                font_path=NAME_FONT_PATH,
                max_font_size=56,
                box_x1=NAME_BOX[0],
                box_x2=NAME_BOX[1],
                box_y1=NAME_BOX[2],
                box_y2=NAME_BOX[3],
                text_color=(255, 255, 255)
            )

            # Add DESIGNATION (auto-fit)
            final = add_text_fit_centered(
                final,
                text=designation_text,
                font_path=DESG_FONT_PATH,
                max_font_size=34,
                box_x1=DESG_BOX[0],
                box_x2=DESG_BOX[1],
                box_y1=DESG_BOX[2],
                box_y2=DESG_BOX[3],
                text_color=(0, 0, 0)
            )

            # Display
            display_width = min(final.width, 900)
            st.image(final, caption="Generated Banner", width=display_width)

            # Download
            img_bytes = io.BytesIO()
            final.save(img_bytes, format="PNG")
            img_bytes.seek(0)

            st.download_button(
                label="Download Banner",
                data=img_bytes,
                file_name="final_banner.png",
                mime="image/png"
            )
