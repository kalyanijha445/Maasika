import os
import random
import sqlite3
import time
import re
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw, ImageFont # Import ImageFont
from fpdf import FPDF
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import platform
from telegram import Bot 

GEMINI_API_KEY = "AIzaSyCLgjLotxkHjQtWr54Nn-cEiyHhUn6fsxI"
EMAIL_SENDER = "info.masika@gmail.com"  
EMAIL_PASSWORD = "tglf gszh exgn gnmz"       
EMAIL_RECEIVER = "vishmapasayat003@gmail.com"
TELEGRAM_BOT_TOKEN = "8299424127:AAFMsj-B27vAK_XRHGnzLYIiLDE1KVf40p0"
TELEGRAM_CHAT_ID = 6667227040  
SAFETY_SETTINGS = [
    {"category": HarmCategory.HARM_CATEGORY_HATE_SPEECH, "threshold": HarmBlockThreshold.BLOCK_NONE},
    {"category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, "threshold": HarmBlockThreshold.BLOCK_NONE},
    {"category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, "threshold": HarmBlockThreshold.BLOCK_NONE},
    {"category": HarmCategory.HARM_CATEGORY_HARASSMENT, "threshold": HarmBlockThreshold.BLOCK_NONE}
]


DB_NAME = "cycle_users.db"
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXT = {"jpg", "jpeg", "png", "bmp", "tiff"}


LANGUAGE_MAP = {
    "en": "English", "as": "Assamese", "bn": "Bengali", "brx": "Bodo", "doi": "Dogri",
    "gu": "Gujarati", "hi": "Hindi", "kn": "Kannada", "ks": "Kashmiri", "kok": "Konkani",
    "mai": "Maithili", "ml": "Malayalam", "mni": "Manipuri", "mr": "Marathi",
    "ne": "Nepali", "or": "Odia", "pa": "Punjabi", "sa": "Sanskrit", "sat": "Santali",
    "sd": "Sindhi", "ta": "Tamil", "te": "Telugu", "ur": "Urdu"
}

app = Flask(__name__)
app.secret_key = "super_secret_key_replace_this"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

genai.configure(api_key=GEMINI_API_KEY)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            email TEXT UNIQUE,
            age INTEGER,
            password TEXT
        )
    ''')
    # --- MODIFICATION START: Add an orders table ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            quantity TEXT NOT NULL,
            user_name TEXT NOT NULL,
            user_email TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            order_time TEXT NOT NULL
        )
    ''')
    # --- MODIFICATION END ---
    conn.commit()
    conn.close()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def _wrap_long_tokens(text, max_len=60):
   
    out = []
    for token in (text or "").split():
        if len(token) <= max_len:
            out.append(token)
        else:
            chunks = [token[i:i+max_len] for i in range(0, len(token), max_len)]
            out.append(" ".join(chunks))
    return " ".join(out)

def sanitize_text_for_pdf(text):
    return text.replace("•", "").encode("latin-1", "replace").decode("latin-1")

def create_pdf_report(patient_name, summary_text, meta: dict):
    
    BRAND_NAME = "MASIKA"
    BRAND_TAGLINE = "Rewrite Your Period Story"
    BRAND_WEBSITE = "https://masika.onrender.com"
    BRAND_EMAIL = "info.masika@gmail.com"
    BRAND_PHONE = "+91 6371646251"
    BRAND_ADDRESS = "BPUT Campus, Biju Patnaik University Of Technology, Odisha, Rourkela - 769015"
    LOGO_PATH = os.path.join("static", "logo.png")
    

    COLOR_PRIMARY_LIGHT = (245, 235, 238)  
    COLOR_ACCENT = (235, 120, 140)         
    COLOR_TEXT_DARK = (45, 45, 45)         
    COLOR_TEXT_MEDIUM = (85, 85, 85)       
    COLOR_TEXT_LIGHT = (140, 140, 140)     
    COLOR_WHITE = (255, 255, 255)
    GRADIENT_START = (255, 255, 255)       
    GRADIENT_END = (252, 240, 243)         

   
    def create_gradient_header(width, height, start_color, end_color, filename):
        img = Image.new("RGB", (width, height), "#FFFFFF")
        draw = ImageDraw.Draw(img)
        r1, g1, b1 = start_color; r2, g2, b2 = end_color
        for i in range(height):
            r = int(r1 + (r2 - r1) * i / height); g = int(g1 + (g2 - g1) * i / height); b = int(b1 + (b2 - b1) * i / height)
            draw.line([(0, i), (width, i)], fill=(r, g, b))
        img.save(filename); return filename


    class PDF(FPDF):
        def footer(self):
            self.set_y(-18)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(*COLOR_TEXT_LIGHT)
            self.set_draw_color(*COLOR_PRIMARY_LIGHT)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(3)
            self.cell(0, 5, BRAND_ADDRESS, 0, 1, 'C')
            self.cell(0, 5, f'Page {self.page_no()}', 0, 0, 'C')

    
    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    try:
        pdf.add_font('Arial', '', 'c:/windows/fonts/arial.ttf', uni=True)
        pdf.add_font('Arial', 'B', 'c:/windows/fonts/arialbd.ttf', uni=True)
        pdf.add_font('Arial', 'I', 'c:/windows/fonts/ariali.ttf', uni=True)
    except RuntimeError:
        print("Arial font not found, falling back to core FPDF fonts.")
    pdf.set_font("Arial", "", 10)

    
    gradient_img_path = create_gradient_header(210, 32, GRADIENT_START, GRADIENT_END, os.path.join(app.config["UPLOAD_FOLDER"], "header_gradient.png"))
    pdf.image(gradient_img_path, 0, 0, 210, 32)
    if os.path.exists(LOGO_PATH):
        pdf.image(LOGO_PATH, 15, 8, 16)

    pdf.set_xy(35, 9); pdf.set_font('Arial', 'B', 20); pdf.set_text_color(*COLOR_TEXT_DARK); pdf.cell(0, 8, BRAND_NAME)
    pdf.set_xy(35, 17); pdf.set_font('Arial', 'I', 9); pdf.set_text_color(*COLOR_TEXT_MEDIUM); pdf.cell(0, 8, BRAND_TAGLINE)
    
    pdf.set_xy(145, 9); pdf.set_font('Arial', '', 8); pdf.set_text_color(*COLOR_TEXT_DARK)
    pdf.cell(0, 5, f"Email: {BRAND_EMAIL}", ln=True, align='R'); pdf.set_x(145)
    pdf.cell(0, 5, f"Phone: {BRAND_PHONE}", ln=True, align='R'); pdf.set_x(145)
    pdf.cell(0, 5, f"Website: {BRAND_WEBSITE}", ln=True, align='R'); pdf.ln(18)

    
    pdf.set_font('Arial', 'B', 20)
    pdf.set_text_color(*COLOR_TEXT_DARK)
    pdf.cell(0, 10, "AI-Analysed Health Report", ln=True, align='C') 
    pdf.ln(12)

   
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(*COLOR_ACCENT)
    pdf.cell(0, 8, "Patient & Report Details", ln=True)
    pdf.set_draw_color(220, 220, 220)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y()); pdf.ln(5)

    def info_row(label, value): 
        pdf.set_font('Arial', 'B', 10); pdf.set_text_color(*COLOR_TEXT_MEDIUM)
        pdf.cell(45, 7, label, align='L')
        pdf.set_font('Arial', '', 10); pdf.set_text_color(*COLOR_TEXT_DARK)
        pdf.cell(5, 7, ":")
        pdf.cell(0, 7, str(value), ln=True)
    
    report_id = f"MSK-{random.randint(100000, 999999)}"
    
    y_start = pdf.get_y()
    pdf.set_x(15); info_row("Patient Name", patient_name)
    pdf.set_x(15); info_row("Patient Age", meta.get("Age", "N/A"))
    pdf.set_x(15); info_row("Typical Cycle Length", f"{meta.get('Cycle Length (days)', 'N/A')} days")
    y_left_end = pdf.get_y()
    
    pdf.set_xy(110, y_start); info_row("Typical Period Duration", f"{meta.get('Period Days', 'N/A')} days")
    pdf.set_x(110); info_row("Report ID", report_id)
    pdf.set_x(110); info_row("Report Generated On", meta.get("Report Generated On", "N/A"))
    y_right_end = pdf.get_y()
    
    pdf.set_y(max(y_left_end, y_right_end) + 5) 

    
    def parse_masika_sections(text):
        sections = {}
        parts = re.split(r'\n*\s*(?=(SUMMARY|WHAT_TO_DO|WHAT_TO_AVOID|DIET_SUGGESTIONS|FOLLOW_UP):)', text)
        for i in range(1, len(parts), 2):
            keyword = parts[i]
           
            content = parts[i+1].lstrip(':').strip()
            
           
            if content.upper().startswith(keyword + ':'):
                content = content[len(keyword)+1:].strip()

            content = re.sub(r'[\*\-]', '•', content) 
            sections[keyword] = content
        return sections

    sections = parse_masika_sections(summary_text)
    section_order = ["SUMMARY", "WHAT_TO_DO", "WHAT_TO_AVOID", "DIET_SUGGESTIONS", "FOLLOW_UP"]

    for title_key in section_order:
        if title_key in sections and sections[title_key]:
            pdf.ln(5)
            
            pdf.set_font('Arial', 'B', 14)
            pdf.set_text_color(*COLOR_WHITE)
           
            pdf.set_fill_color(*COLOR_ACCENT) 
            section_title = f"  {title_key.replace('_', ' ').title()}  "
            pdf.cell(pdf.get_string_width(section_title) + 5, 9, section_title, ln=True, fill=True); pdf.ln(4)

            pdf.set_font('Arial', '', 10.5)
            pdf.set_text_color(*COLOR_TEXT_DARK)
            content_lines = [line.strip() for line in sections[title_key].split('\n') if line.strip()]
            
           
            for idx, line in enumerate(content_lines, start=1):
                line = sanitize_text_for_pdf(line) 
                if line.startswith('•'):
                    pdf.set_x(15)
                    pdf.cell(5, 6, f"{idx}.")  
                    pdf.multi_cell(180, 6, line[1:].strip())
                else: 
                    pdf.set_x(10)
                    pdf.multi_cell(190, 6, line)
                pdf.ln(2)
           
    pdf.set_y(-45)
    pdf.set_fill_color(*COLOR_PRIMARY_LIGHT)
    pdf.rect(10, pdf.get_y() - 2, 190, 19, 'F')
    
    pdf.set_xy(12, pdf.get_y()); pdf.set_font('Arial', 'B', 9); pdf.set_text_color(*COLOR_TEXT_MEDIUM); pdf.cell(0, 6, "Disclaimer", ln=True)
    pdf.set_x(12); pdf.set_font('Arial', 'I', 8)
    pdf.multi_cell(186, 4, "This is an AI-assisted report generated by MASIKA for informational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always consult a qualified healthcare provider for any medical concerns.")
    
   
    fname = f"{patient_name.replace(' ', '_')}_masika_report_{int(time.time())}.pdf"
    out_path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
    pdf.output(out_path)
    return out_path



def image_to_text_via_gemini(image_path):
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        with open(image_path, "rb") as f:
            img_bytes = f.read()
            img_part = {"mime_type": "image/jpeg", "data": img_bytes}
            prompt_parts = [
                img_part,
                "Please extract any lab values (name:value pairs) from this lab report image. Return results as 'Marker: Value' lines. If none found, say 'NO_VALUES_FOUND'.",
            ]
            response = model.generate_content(prompt_parts, safety_settings=SAFETY_SETTINGS)
        return response.text
    except Exception as e:
        return f"ERROR_READING_IMAGE: {e}"

def parse_lab_values_text(extracted_text):
    values = {}
    if not extracted_text:
        return values
    for line in extracted_text.splitlines():
        line = line.strip()
        if not line: continue
        parts = re.split(r'[:=-]', line, 1)
        if len(parts) != 2:
            m = re.search(r"([A-Za-z\s\/]+)\s+([\d\.]+)", line)
            if m:
                parts = [m.group(1).strip(), m.group(2)]
            else:
                continue
        key = parts[0].strip()
        val = parts[1].strip()
        if key and val:
            values[key] = val
    return values

def generate_recommendations_from_inputs(age, cycle_days, period_days, description, lab_values, language="en"):
    model = genai.GenerativeModel("gemini-2.5-flash")
    language_name = LANGUAGE_MAP.get(language, "English")
    
    prompt_lines = [
        "You are an expert AI health assistant specializing in women's cyclical health. Your primary task is to perform an integrated analysis by deeply correlating the user's written symptoms with their lab results, all within the context of their age and cycle data. Your response must be highly personalized based on these connections. Crucially, you MUST NOT give a medical diagnosis. Instead, provide intelligent insights and safe, actionable suggestions.",
        f"IMPORTANT: All explanatory text and suggestions must be in the '{language_name}' language. However, the section keywords ('SUMMARY:', 'WHAT_TO_DO:', etc.) MUST remain in English.",
        "Structure your response with these exact keywords, each on a new line: SUMMARY:, WHAT_TO_DO:, WHAT_TO_AVOID:, DIET_SUGGESTIONS:, FOLLOW_UP:",
        "For the SUMMARY: section, provide a concise paragraph that explicitly connects the user's symptoms (e.g., fatigue, pain) with specific lab values (e.g., low hemoglobin). Acknowledge their age as a contributing factor.",
        "For the WHAT_TO_DO:, DIET_SUGGESTIONS:, etc., sections, ensure every bullet point (*) is a direct consequence of the analysis. For example, if symptoms suggest fatigue AND labs show low iron, a diet suggestion MUST specifically mention iron-rich foods and explain that it targets the suspected iron deficiency causing the fatigue. Do not give generic advice. All advice must be justified by the provided user data.",
        "\n--- Patient Data for Integrated Analysis ---",
        f"Age: {age}",
        f"Typical cycle length (days): {cycle_days}",
        f"Period duration (days): {period_days}",
        f"User-described Symptoms & Situation: {description or 'None provided'}",
        "Lab Values from Report (connect these to the symptoms):",
    ]
    
    if lab_values:
        for k, v in lab_values.items():
            prompt_lines.append(f"{k}: {v}")
    else:
        prompt_lines.append("No lab values were provided or could be extracted.")
    
    prompt = "\n".join(prompt_lines)
    
    try:
        response = model.generate_content([prompt], safety_settings=SAFETY_SETTINGS)
        return response.text
    except Exception as e:
        return f"ERROR_GENERATING_RECOMMENDATIONS: {e}"

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_email" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def create_order_image_card(details):
    """
    Generates a visually appealing, high-resolution PNG image card for a new product order.
    Args:
        details (dict): A dictionary containing order information.
    Returns:
        str: The file path of the generated PNG image.
    """
    from textwrap import wrap
    
    # --- Card Configuration ---
    scale = 2
    width = 800 * scale
    padding = 70 * scale
    LOGO_PATH = os.path.join("static", "logo.png")

    # --- Professional Color Palette ---
    bg_color = (255, 255, 255)
    header_gradient_start = (255, 243, 245)
    header_gradient_end = (252, 238, 241)
    text_color = (30, 30, 30)
    label_color = (100, 100, 100)
    accent_color = (211, 75, 96)
    brand_title_color = (190, 60, 80)
    line_color = (235, 235, 235)

    # --- Advanced Font Setup ---
    def get_font(style='regular', size=24):
        font_map = {
            'windows': {'bold': 'C:/Windows/Fonts/segoeuib.ttf', 'regular': 'C:/Windows/Fonts/segoeui.ttf', 'light': 'C:/Windows/Fonts/segoeuil.ttf'},
            'linux': {'bold': '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'regular': '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 'light': '/usr/share/fonts/truetype/dejavu/DejaVuSans-ExtraLight.ttf'},
            'fallback': {'bold': 'arialbd.ttf', 'regular': 'arial.ttf', 'light': 'arial.ttf'}
        }
        system = platform.system().lower()
        preferred = font_map.get('windows' if 'windows' in system else 'linux', font_map['fallback'])
        font_path = preferred.get(style, preferred['regular'])
        try:
            return ImageFont.truetype(font_path, size)
        except IOError:
            try:
                font_path = font_map['fallback'].get(style, font_map['fallback']['regular'])
                return ImageFont.truetype(font_path, size)
            except IOError:
                 return ImageFont.load_default()

    font_title = get_font('bold', 70 * scale)
    font_tagline = get_font('regular', 24 * scale)
    font_header = get_font('bold', 38 * scale)
    font_label = get_font('regular', 28 * scale)
    font_value = get_font('bold', 28 * scale)
    font_address = get_font('regular', 26 * scale)

    # --- Dynamic Drawing Logic ---
    draw_list = []
    
    # 1. Header
    header_height = int(200 * scale)

    # BUG FIX: Added a second, unused parameter `_y` to match the calling signature in the loop.
    def draw_header(draw_obj, _y):
        for y in range(header_height):
            r = int(header_gradient_start[0] + (header_gradient_end[0] - header_gradient_start[0]) * y / header_height)
            g = int(header_gradient_start[1] + (header_gradient_end[1] - header_gradient_start[1]) * y / header_height)
            b = int(header_gradient_start[2] + (header_gradient_end[2] - header_gradient_start[2]) * y / header_height)
            draw_obj.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Temp image needed for pasting RGBA logo onto an RGB background
        temp_img_for_paste = Image.new('RGB', (width, header_height))
        
        if os.path.exists(LOGO_PATH):
            logo_size = int(120 * scale)
            logo_img = Image.open(LOGO_PATH).convert("RGBA")
            logo_img.thumbnail((logo_size, logo_size), Image.Resampling.LANCZOS)
            logo_y = (header_height - logo_size) // 2
            
            # Paste logo onto the main image
            img.paste(logo_img, (padding, logo_y), logo_img)
            text_x_start = padding + logo_size + int(30 * scale)
        else:
            text_x_start = padding
        
        draw_obj.text((text_x_start, 60 * scale), "MASIKA", font=font_title, fill=brand_title_color)
        draw_obj.text((text_x_start, int(60 * scale + 75*scale*0.95)), "Rewrite Your Period Story", font=font_tagline, fill=label_color)

    draw_list.append({'func': draw_header, 'height': header_height})
    draw_list.append({'func': None, 'height': padding})

    # 2. Section: New Order Received
    draw_list.append({'func': lambda d, y: d.text((padding, y), "New Order Received", font=font_header, fill=accent_color), 'height': int(65*scale)})
    
    value_start_x = 300 * scale # <<< MODIFIED: Changed from 420 to 300 to give more space for the value text.
    line_wrap_width = 32

    def create_row_drawable(label, value, value_color=text_color):
        wrapped_value = '\n'.join(wrap(str(value), width=line_wrap_width)) # Ensure value is a string
        temp_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
        bbox = temp_draw.multiline_textbbox((0,0), wrapped_value, font=font_value, spacing=int(10*scale))
        height = (bbox[3] - bbox[1]) + int(30 * scale)

        def draw_func(d, y):
            d.text((padding, y), label, font=font_label, fill=label_color)
            d.multiline_text((value_start_x, y), wrapped_value, font=font_value, fill=value_color, spacing=int(10*scale))
        
        return {'func': draw_func, 'height': height}
    
    draw_list.append(create_row_drawable("Product:", details['product_name']))
    draw_list.append(create_row_drawable("Quantity:", details['quantity']))
    draw_list.append(create_row_drawable("Order Time:", details['time']))
    
    def create_divider_drawable():
        height = int(90 * scale)
        def draw_func(d, y):
            divider_y = y + (height // 2) - int(15 * scale)
            d.line([(padding, divider_y), (width - padding, divider_y)], fill=line_color, width=3*scale)
        return {'func': draw_func, 'height': height}
        
    draw_list.append(create_divider_drawable())

    # 3. Section: Customer Information
    draw_list.append({'func': lambda d, y: d.text((padding, y), "Customer Information", font=font_header, fill=accent_color), 'height': int(65*scale)})
    draw_list.append(create_row_drawable("Name:", details['user_name']))
    draw_list.append(create_row_drawable("Email:", details['user_email'], accent_color))
    draw_list.append(create_row_drawable("Phone:", details['phone']))
    
    draw_list.append(create_divider_drawable())

    # 4. Section: Shipping Address
    draw_list.append({'func': lambda d, y: d.text((padding, y), "Shipping Address", font=font_header, fill=accent_color), 'height': int(65*scale)})
    
    # Address does not have a label, so it's handled differently
    address_value = details['address']
    wrapped_address = '\n'.join(wrap(address_value, width=line_wrap_width*2)) # Address can be wider
    temp_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
    bbox = temp_draw.multiline_textbbox((0,0), wrapped_address, font=font_address, spacing=int(10*scale))
    address_height = (bbox[3] - bbox[1]) + int(20 * scale)
    draw_list.append({'func': lambda d, y: d.multiline_text((padding, y), wrapped_address, font=font_address, fill=text_color, spacing=int(10*scale)), 'height': address_height})

    # --- Calculate Total Height and Create Canvas ---
    total_height = sum(item['height'] for item in draw_list) + padding
    img = Image.new('RGB', (width, total_height), bg_color)
    draw = ImageDraw.Draw(img)

    # --- Execute All Drawing Functions ---
    current_y = 0
    for item in draw_list:
        if item['func']:
            item['func'](draw, current_y)
        current_y += item['height']

    # --- Finalize and Save ---
    filename = f"order_{int(time.time())}.png"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    img.save(filepath, "PNG", quality=95, optimize=True)
    return filepath


@app.route('/order_product', methods=['POST'])
@login_required
def order_product():
    product_name = request.form.get('product_name', 'Unknown Product')
    quantity = request.form.get('quantity', '1')
    address = request.form.get('address', '').strip()
    phone = request.form.get('phone', '').strip()

    user_name = session.get('user_name', 'Unknown User')
    user_email = session.get('user_email', 'No Email Provided')

    if not address or not phone:
        return jsonify({'success': False, 'message': 'Address and phone number are required.'})
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    order_details = {
        'product_name': product_name,
        'quantity': quantity,
        'user_name': user_name,
        'user_email': user_email,
        'phone': phone,
        'address': address,
        'time': current_time,
    }

    # --- MODIFICATION START: Save order to the database instead of session ---
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute(
            "INSERT INTO orders (product_name, quantity, user_name, user_email, phone, address, order_time) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                order_details['product_name'],
                order_details['quantity'],
                order_details['user_name'],
                order_details['user_email'],
                order_details['phone'],
                order_details['address'],
                order_details['time']
            )
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DATABASE ERROR: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to save order details.'})
    # --- MODIFICATION END ---


    image_path = None
    try:
        # Generate the beautiful image card
        image_path = create_order_image_card(order_details)
        
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        caption = f" ✨ New Order Received! ✨ from {user_name} !"

        # Send the generated image to Telegram
        with open(image_path, 'rb') as photo_file:
            bot.send_photo(
                chat_id=TELEGRAM_CHAT_ID,
                photo=photo_file,
                caption=caption
            )
        
        message = 'Order placed successfully! A visual notification has been sent.'
        return jsonify({'success': True, 'message': message})

    except Exception as e:
        error_message = f'Failed to send Telegram notification. Error: {str(e)}'
        print(f"TELEGRAM/IMAGE GEN ERROR: {error_message}")
        return jsonify({'success': False, 'message': error_message})
    finally:
        # Clean up the generated image file
        if image_path and os.path.exists(image_path):
            os.remove(image_path)


@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email").strip()
        password = request.form.get("password").strip() 
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT full_name, age, password FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        if user:
            session["user_email"] = email
            session["user_name"] = user[0]
            session["user_age"] = user[1]
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("User not found. Please sign up.", "danger")
            return redirect(url_for("signup"))
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        full_name = request.form.get("full_name").strip()
        email = request.form.get("email").strip()
        age = request.form.get("age").strip()
        password = request.form.get("password").strip()  

        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute(
                "INSERT INTO users (full_name, email, age, password) VALUES (?, ?, ?, ?)",
                (full_name, email, age, password)
            )
            conn.commit()
            conn.close()
            session["user_email"] = email
            session["user_name"] = full_name
            session["user_age"] = age
            flash("Signup successful! Logged in automatically.", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("Email already exists. Please login.", "danger")
            return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    result = None
    pdf_link = None
    extracted_images = {}
    parsed_values = {}
    if request.method == "POST":
        patient_name = session.get("user_name", "Anonymous")
        age = session.get("user_age", "")
        cycle_days = request.form.get("cycle_days", "").strip()
        period_days = request.form.get("period_days", "").strip()
        description = request.form.get("description", "").strip()
        selected_language = request.form.get("selected_language", "en").strip()

        uploaded_files = request.files.getlist("report_images")
        for f in uploaded_files:
            if f and allowed_file(f.filename):
                fn = secure_filename(f.filename)
                fname = f"{int(time.time())}_{random.randint(1000,9999)}_{fn}"
                path = os.path.join(app.config["UPLOAD_FOLDER"], fname)
                f.save(path)
                
                extracted = image_to_text_via_gemini(path)
                extracted_images[path] = extracted
                parsed = parse_lab_values_text(extracted)
                parsed_values.update(parsed) 
        
        recommendations_text = generate_recommendations_from_inputs(
            age, cycle_days, period_days, description, parsed_values, selected_language
        )
        result = {
            "patient_name": patient_name,
            "age": age,
            "cycle_days": cycle_days,
            "period_days": period_days,
            "description": description,
            "parsed_values": parsed_values,
            "recommendations_raw": recommendations_text,
            "extracted_images": extracted_images
        }

        meta = {
            "Name": patient_name,
            "Age": age or "Not provided",
            "Cycle Length (days)": cycle_days or "Not provided",
            "Period Days": period_days or "Not provided",
            "Report Generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
      
        if selected_language == "en":
            pdf_path = create_pdf_report(patient_name, recommendations_text, meta)
            pdf_link = url_for("download_file", filename=os.path.basename(pdf_path))
        else:
            pdf_link = None
       
    return render_template("dashboard.html", result=result, pdf_link=pdf_link)

@app.route("/admin_dashboard")
@login_required
def admin_dashboard():
    # --- MODIFICATION START: Fetch ALL orders from the database ---
    all_orders = []
    try:
        conn = sqlite3.connect(DB_NAME)
        # This makes the cursor return rows as dictionary-like objects
        conn.row_factory = sqlite3.Row 
        c = conn.cursor()
        # Fetch all orders, newest first
        c.execute("SELECT * FROM orders ORDER BY id DESC")
        rows = c.fetchall()
        # Convert row objects to standard dictionaries for the template
        all_orders = [dict(row) for row in rows]
        conn.close()
    except Exception as e:
        print(f"DATABASE FETCH ERROR: {str(e)}")
        flash("Could not retrieve order information.", "danger")
        
    return render_template("admin_dashboard.html", orders=all_orders)
    # --- MODIFICATION END ---

@app.route("/products")
@login_required
def products():
    return render_template("products.html")

@app.route("/videos")
@login_required
def videos():
    return render_template("videos.html")

@app.route("/consultation", methods=["GET", "POST"])
@login_required
def consultation():
    if request.method == "POST":
        flash("Consultation request submitted!", "success")
    return render_template("consultation.html")

@app.route("/download/<filename>")
@login_required
def download_file(filename):
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if not os.path.exists(path):
        flash("File not found", "danger")
        return redirect(url_for("dashboard"))
    return send_file(path, as_attachment=True)

@app.route("/ping")
def ping():
    return "OK", 200

@app.route("/logout")
@login_required
def logout():
    session.pop("user_email", None)
    session.pop("user_name", None)
    session.pop("user_age", None)
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
