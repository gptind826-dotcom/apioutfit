from flask import Flask, request, send_file, jsonify
import requests
import io
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# API URLs
INFO_API = "https://mafuuuu-info-api.vercel.app/mafu-info"
ICON_API = "https://mafu-icon-api.onrender.com/icon"

# ========== NEW BACKGROUND: STAGGERED HONEYCOMB LAYOUT ==========
# Template: outfit_v2.png (1184x864) - Premium dark navy/gold design
# Larger hexagonal hitboxes for better item visibility

OUTFIT_BOXES = [
    # Left side - staggered honeycomb
    {"pos": (50, 125),  "size": (230, 195), "label": "Outfit 1"},   # Top left
    {"pos": (260, 295), "size": (230, 195), "label": "Outfit 2"},   # Mid left (staggered in)
    {"pos": (50, 465),  "size": (230, 195), "label": "Outfit 3"},   # Bottom left
    # Right side - staggered honeycomb
    {"pos": (900, 125), "size": (230, 195), "label": "Outfit 4"},   # Top right
    {"pos": (690, 295), "size": (230, 195), "label": "Outfit 5"},   # Mid right (staggered in)
    {"pos": (900, 465), "size": (230, 195), "label": "Outfit 6"},   # Bottom right
]

# Player info bar at bottom
PLAYER_BAR_Y = 795
PLAYER_BAR_X_START = 320
PLAYER_BAR_X_END = 870
PLAYER_BAR_HEIGHT = 50

# Template dimensions
TEMPLATE_WIDTH = 1184
TEMPLATE_HEIGHT = 864


@app.route('/mafu-outfit')
def mafu_outfit():
    uid = request.args.get('uid')
    key = request.args.get('key')

    if key != 'mafu':
        return jsonify({"error": "Invalid key"}), 403

    if not uid:
        return jsonify({"error": "UID required"}), 400

    # ========== REAL-TIME API CALL ==========
    try:
        info_res = requests.get(
            f"{INFO_API}?uid={uid}",
            timeout=15,
            headers={'Cache-Control': 'no-cache'}
        )
        info_data = info_res.json()

        if info_res.status_code != 200 or info_data.get('error'):
            return jsonify({
                "error": info_data.get('error', 'Player Not Found')
            }), info_res.status_code

    except Exception as e:
        return jsonify({"error": f"API Error: {str(e)}"}), 500

    # ========== PARSE REAL-TIME DATA ==========
    profile = info_data.get('profileInfo', {})
    clothes = profile.get('clothes', [])

    basic_info = info_data.get('basicInfo', {})
    player_name = basic_info.get('nickname', f'UID_{uid}')
    player_level = basic_info.get('level', 'N/A')

    # ========== LOAD TEMPLATE ==========
    try:
        template = Image.open('outfit.png').convert('RGBA')
    except FileNotFoundError:
        return jsonify({"error": "outfit.png not found"}), 500

    # Ensure template is correct size
    if template.size != (TEMPLATE_WIDTH, TEMPLATE_HEIGHT):
        template = template.resize((TEMPLATE_WIDTH, TEMPLATE_HEIGHT), Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(template)
    width, height = template.size

    # ========== FONTS ==========
    try:
        font = ImageFont.truetype("/system/fonts/Roboto-Bold.ttf", 28)
        small_font = ImageFont.truetype("/system/fonts/Roboto-Regular.ttf", 18)
        id_font = ImageFont.truetype("/system/fonts/Roboto-Regular.ttf", 15)
    except:
        font = ImageFont.load_default()
        small_font = font
        id_font = font

    # ========== DRAW PLAYER INFO BAR ==========
    # Cover template placeholder with semi-transparent bar
    bar_overlay = Image.new('RGBA', template.size, (0, 0, 0, 0))
    bar_draw = ImageDraw.Draw(bar_overlay)
    bar_draw.rectangle(
        [PLAYER_BAR_X_START, PLAYER_BAR_Y, PLAYER_BAR_X_END, PLAYER_BAR_Y + PLAYER_BAR_HEIGHT],
        fill=(10, 10, 25, 210)
    )
    template = Image.alpha_composite(template, bar_overlay)
    draw = ImageDraw.Draw(template)

    # Draw player info (gold text with shadow)
    info_text = f"Player: {player_name}  |  Level: {player_level}  |  UID: {uid}"
    bbox = draw.textbbox((0, 0), info_text, font=font)
    text_w = bbox[2] - bbox[0]
    x_pos = (width - text_w) // 2
    y_pos = PLAYER_BAR_Y + 10

    draw.text((x_pos + 2, y_pos + 2), info_text, fill=(0, 0, 0), font=font)       # Shadow
    draw.text((x_pos, y_pos), info_text, fill=(255, 215, 0), font=font)             # Gold

    # ========== DRAW OUTFIT ICONS ==========
    for i, item_id in enumerate(clothes[:6]):
        box = OUTFIT_BOXES[i]
        x, y = box["pos"]
        w, h = box["size"]

        # Subtle highlight border inside hexagon
        draw.rectangle([x, y, x + w, y + h], outline=(255, 215, 0, 60), width=1)

        try:
            # Fetch icon from API
            icon_res = requests.get(
                f"{ICON_API}?key=MAFU&item_id={item_id}",
                timeout=10,
                headers={'Cache-Control': 'no-cache'}
            )

            if icon_res.status_code == 200 and len(icon_res.content) > 100:
                # Load and resize icon to fit inside box with padding
                icon = Image.open(io.BytesIO(icon_res.content)).convert('RGBA')
                padding = 20
                icon_w = w - (padding * 2)
                icon_h = h - (padding * 2)
                icon = icon.resize((icon_w, icon_h), Image.Resampling.LANCZOS)

                # Center icon in box
                ix = x + padding
                iy = y + padding
                template.paste(icon, (ix, iy), icon)

            else:
                # API failed - show item ID centered
                id_text = str(item_id)
                tb = draw.textbbox((0, 0), id_text, font=small_font)
                tw = tb[2] - tb[0]
                th = tb[3] - tb[1]
                tx = x + (w - tw) // 2
                ty = y + (h - th) // 2
                draw.text((tx, ty), id_text, fill=(255, 100, 100), font=small_font)
                draw.rectangle([x, y, x + w, y + h], outline=(255, 50, 50), width=2)

        except Exception:
            # Error - red X
            draw.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=2)
            draw.line([x + 15, y + 15, x + w - 15, y + h - 15], fill=(255, 0, 0), width=3)
            draw.line([x + w - 15, y + 15, x + 15, y + h - 15], fill=(255, 0, 0), width=3)

    # ========== EMPTY SLOTS ==========
    for i in range(len(clothes), 6):
        box = OUTFIT_BOXES[i]
        x, y = box["pos"]
        w, h = box["size"]
        draw.rectangle([x, y, x + w, y + h], outline=(80, 80, 120, 80), width=1)
        tb = draw.textbbox((0, 0), "Empty", font=small_font)
        tw = tb[2] - tb[0]
        th = tb[3] - tb[1]
        tx = x + (w - tw) // 2
        ty = y + (h - th) // 2
        draw.text((tx, ty), "Empty", fill=(100, 100, 100), font=small_font)

    # ========== RETURN IMAGE ==========
    output = io.BytesIO()
    template.save(output, format='PNG')
    output.seek(0)

    return send_file(output, mimetype='image/png')


@app.route('/test')
def test_api():
    """Test endpoint - returns JSON data for debugging"""
    uid = request.args.get('uid')
    if not uid:
        return jsonify({"error": "UID required"}), 400

    try:
        r = requests.get(f"{INFO_API}?uid={uid}", timeout=15)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/')
def home():
    return {
        "api": "Mafu Outfit API v2 (New Design)",
        "template": "1184x864 Honeycomb Design",
        "usage": "/mafu-outfit?uid=UID&key=mafu",
        "test": "/test?uid=UID (JSON data check)"
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
turn jsonify({"error": "UID required"}), 400

    try:
        r = requests.get(f"{INFO_API}?uid={uid}", timeout=15)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/')
def home():
    return {
        "api": "Mafu Outfit API (Fixed)",
        "usage": "/mafu-outfit?uid=UID&key=mafu",
        "test": "/test?uid=UID (JSON data check)"
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
