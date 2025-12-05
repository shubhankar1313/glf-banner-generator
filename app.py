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

NAME_BOX_X1 = 278
NAME_BOX_X2 = 800
NAME_BOX_Y1 = 705
NAME_BOX_Y2 = 790
NAME_BOX_HEIGHT = NAME_BOX_Y2 - NAME_BOX_Y1
NAME_FONT_PATH = "assets/Khand-SemiBold.ttf"
MAX_NAME_FONT = 66

DESG_FONT = "assets/Poppins-SemiBold.ttf"

# Image Functions

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


def add_text_fit_centered(
    base_image,
    text,
    font_path,
    max_font_size,
    box_x1,
    box_x2,
    box_y1,
    box_y2,
    min_font_size=12,
    text_color=(255, 255, 255)
):
    """
    Draw text horizontally & vertically centered inside the given box.
    Shrinks font size automatically if the text exceeds the width.
    """

    draw = ImageDraw.Draw(base_image)
    allowed_width = box_x2 - box_x1
    allowed_height = box_y2 - box_y1

    # 1) Try largest font size
    font_size = max_font_size
    font = ImageFont.truetype(font_path, font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]

    # 2) Shrink if wider than allowed area
    if text_width > allowed_width:
        scale = allowed_width / text_width
        font_size = max(min_font_size, int(font_size * scale))

        # Rebuild font with new size
        font = ImageFont.truetype(font_path, font_size)
        bbox = draw.textbbox((0, 0), text, font=font)

    # 3) Now compute final bounding box
    text_width  = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # 4) Horizontal center of the image (since your box is centered)
    image_w = base_image.width
    x = (image_w - text_width) // 2

    # 5) Vertical center inside the box
    box_center_y = (box_y1 + box_y2) // 2
    y = box_center_y - (text_height // 2)

    # 6) Draw
    draw.text((x, y), text, font=font, fill=text_color)

    return base_image, font_size

# Streamlit UI

st.set_page_config(page_title="Banner Generator", layout="centered")
st.title("Banner Generator")
st.write("Upload a photo, enter the name & designation, and generate your banner.")

uploaded_file = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"])

name_text = st.text_input("Full Name", "")
designation_text = st.text_input("Designation", "")

generate_btn = st.button("Generate Banner")

if generate_btn:
    if uploaded_file is None:
        st.error("Please upload a photo.")
    elif name_text.strip() == "" or designation_text.strip() == "":
        st.error("Please enter name and designation.")
    else:
        # Load banner
        if not os.path.exists(BANNER_PATH):
            st.error(f"Banner template not found at '{BANNER_PATH}'.")
        else:
            banner = Image.open(BANNER_PATH).convert("RGBA")

            # Load uploaded image
            person_img = Image.open(uploaded_file).convert("RGBA")

            # Process image
            person_img = resize_input_image(person_img)
            fitted_img = fit_image_to_slot(person_img, SLOT_W, SLOT_H)

            background = Image.new("RGBA", banner.size, (0, 0, 0, 0))
            background.paste(fitted_img, (SLOT_X, SLOT_Y))

            final = Image.alpha_composite(background, banner)

            # Add text (Name)
            final, used_font = add_text_fit_centered(
                final,
                text=name_text,
                font_path="assets/Khand-SemiBold.ttf",
                max_font_size=66,
                box_x1=288,
                box_x2=790,
                box_y1=705,
                box_y2=790,
                min_font_size=12,
                text_color=(255, 255, 255)
            )

            # Add text (Designation)
            final, used_font = add_text_fit_centered(
                final,
                text=designation_text,
                font_path="assets/Poppins-SemiBold.ttf",
                max_font_size=32,
                box_x1=367,
                box_x2=712,
                box_y1=807,
                box_y2=855,
                min_font_size=12,
                text_color=(0, 0, 0)
            )

            # Display output
            display_width = min(final.width, 900)
            st.image(final, caption="Generated Banner", width=display_width)

            # Download button
            img_bytes = io.BytesIO()
            final.save(img_bytes, format="PNG")
            img_bytes.seek(0)

            st.download_button(
                label="Download Banner",
                data=img_bytes,
                file_name="final_banner.png",
                mime="image/png"
            )
