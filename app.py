from flask import Flask, request, send_file, jsonify
import requests
import io
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# API URLs
INFO_API = "https://mafuuuu-info-api.vercel.app/mafu-info"
ICON_API = "https://mafu-icon-api.onrender.com/icon"

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
        
        # Real error from API
        if info_res.status_code != 200 or info_data.get('error'):
            return jsonify({
                "error": info_data.get('error', 'Player Not Found')
            }), info_res.status_code
            
    except Exception as e:
        return jsonify({"error": f"API Error: {str(e)}"}), 500
    
    # ========== PARSE REAL-TIME DATA ==========
    profile = info_data.get('profileInfo', {})
    
    avatar_id = profile.get('avatarId', 0)
    skin_color = profile.get('skinColor', 0)
    clothes = profile.get('clothes', [])  # [203042024, 214000050, ...]
    
    # Basic info (যদি থাকে)
    basic_info = info_data.get('basicInfo', {})
    player_name = basic_info.get('nickname', f'UID_{uid}')
    player_level = basic_info.get('level', 'N/A')
    
    # ========== LOAD TEMPLATE ==========
    try:
        template = Image.open('outfit.png').convert('RGBA')
    except FileNotFoundError:
        return jsonify({"error": "outfit.png not found"}), 500
    
    draw = ImageDraw.Draw(template)
    width, height = template.size
    
    # ========== FONT ==========
    try:
        font = ImageFont.truetype("/system/fonts/Roboto-Bold.ttf", 28)
        small_font = ImageFont.truetype("/system/fonts/Roboto-Regular.ttf", 16)
    except:
        font = ImageFont.load_default()
        small_font = font
    
    # ========== DRAW PLAYER INFO ==========
    info_text = f"Player: {player_name} | Level: {player_level} | UID: {uid}"
    
    # Center text
    bbox = draw.textbbox((0,0), info_text, font=font)
    text_w = bbox[2] - bbox[0]
    x_pos = (width - text_w) // 2
    y_pos = height - 55
    
    draw.text((x_pos+2, y_pos+2), info_text, fill=(0,0,0), font=font)
    draw.text((x_pos, y_pos), info_text, fill=(255,255,255), font=font)
    
    # ========== OUTFIT BOXES (তোমার template অনুযায়ী) ==========
    # Left side: Outfit 1,2,3 | Right side: Outfit 4,5,6
    outfit_boxes = [
        {"pos": (55, 85), "size": (90, 90), "label": "Outfit 1"},   # Left top
        {"pos": (55, 215), "size": (90, 90), "label": "Outfit 2"},  # Left mid
        {"pos": (55, 345), "size": (90, 90), "label": "Outfit 3"},  # Left bottom
        {"pos": (625, 85), "size": (90, 90), "label": "Outfit 4"},  # Right top
        {"pos": (625, 215), "size": (90, 90), "label": "Outfit 5"}, # Right mid
        {"pos": (625, 345), "size": (90, 90), "label": "Outfit 6"}, # Right bottom
    ]
    
    # ========== REAL-TIME: FETCH & DRAW OUTFIT ICONS ==========
    for i, item_id in enumerate(clothes[:6]):
        box = outfit_boxes[i]
        x, y = box["pos"]
        w, h = box["size"]
        
        # Box border (default)
        draw.rectangle([x, y, x+w, y+h], outline=(100,100,255), width=2)
        
        try:
            # REAL-TIME API CALL: Fetch icon
            icon_res = requests.get(
                f"{ICON_API}?key=MAFU&item_id={item_id}",
                timeout=10,
                headers={'Cache-Control': 'no-cache'}
            )
            
            if icon_res.status_code == 200 and len(icon_res.content) > 100:
                # Load icon
                icon = Image.open(io.BytesIO(icon_res.content)).convert('RGBA')
                icon = icon.resize((w-10, h-10), Image.Resampling.LANCZOS)
                
                # Center in box
                ix = x + 5
                iy = y + 5
                
                # Paste with transparency
                template.paste(icon, (ix, iy), icon)
                
                # Item ID text below
                id_text = str(item_id)
                tb = draw.textbbox((0,0), id_text, font=small_font)
                tw = tb[2] - tb[0]
                draw.text((x + (w-tw)//2, y + h + 3), id_text, fill=(200,200,255), font=small_font)
                
            else:
                # API failed - show item ID only
                id_text = str(item_id)
                tb = draw.textbbox((0,0), id_text, font=small_font)
                tw = tb[2] - tb[0]
                th = tb[3] - tb[1]
                tx = x + (w - tw) // 2
                ty = y + (h - th) // 2
                draw.text((tx, ty), id_text, fill=(255,100,100), font=small_font)
                draw.rectangle([x, y, x+w, y+h], outline=(255,50,50), width=2)
                
        except Exception as e:
            # Error - red X
            draw.rectangle([x, y, x+w, y+h], outline=(255,0,0), width=2)
            draw.line([x, y, x+w, y+h], fill=(255,0,0), width=2)
            draw.line([x+w, y, x, y+h], fill=(255,0,0), width=2)
    
    # Empty slots
    for i in range(len(clothes), 6):
        box = outfit_boxes[i]
        x, y = box["pos"]
        w, h = box["size"]
        draw.rectangle([x, y, x+w, y+h], outline=(80,80,120,100), width=1)
        draw.text((x+10, y+h//2), "Empty", fill=(100,100,100), font=small_font)
    
    # ========== RETURN IMAGE ==========
    output = io.BytesIO()
    template.save(output, format='PNG')
    output.seek(0)
    
    return send_file(output, mimetype='image/png')

@app.route('/test')
def test_api():
    """Test korar jonno - JSON data dekhabe"""
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
        "api": "Mafu Outfit API",
        "usage": "/mafu-outfit?uid=UID&key=mafu",
        "test": "/test?uid=UID (JSON data check)"
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)