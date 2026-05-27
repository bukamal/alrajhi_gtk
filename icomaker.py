import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

# ================== الإعدادات ==================
SIZE = 512  # حجم الأيقونة الأساسي (سيتم إنشاء أحجام متعددة)
OUTPUT_ICO = "alrajhi_icon.ico"
OUTPUT_PNG = "alrajhi_logo.png"

# ألوان التدرج (ذهبي + أخضر داكن)
COLOR_GRADIENT_START = (26, 67, 43)   # أخضر غامق
COLOR_GRADIENT_END = (218, 165, 32)   # ذهبي
COLOR_ACCENT = (255, 215, 0)          # ذهبي فاتح
COLOR_BG = (15, 25, 35)               # خلفية سوداء مائلة للزرقة

# ================== دوال مساعدة ==================
def create_gradient_image(width, height, start_color, end_color):
    """إنشاء صورة بتدرج لوني"""
    img = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(start_color[0] * (1 - ratio) + end_color[0] * ratio)
        g = int(start_color[1] * (1 - ratio) + end_color[1] * ratio)
        b = int(start_color[2] * (1 - ratio) + end_color[2] * ratio)
        draw.line((0, y, width, y), fill=(r, g, b, 255))
    return img

def add_shadow(img, offset=5, blur=10):
    """إضافة ظل خفيف للخلفية"""
    shadow = img.copy()
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    shadow = ImageOps.expand(shadow, border=offset, fill=(0, 0, 0, 0))
    result = Image.new("RGBA", (img.width + offset * 2, img.height + offset * 2), (0, 0, 0, 0))
    result.paste(shadow, (offset, offset))
    result.paste(img, (offset, offset), img)
    return result

def draw_scales(draw, center_x, center_y, size, color):
    """رسم رمز الميزان (كفتين)"""
    # قاعدة الميزان (خط أفقي)
    bar_width = int(size * 0.6)
    bar_height = int(size * 0.1)
    draw.rectangle([center_x - bar_width//2, center_y - bar_height//2,
                    center_x + bar_width//2, center_y + bar_height//2], fill=color, outline=None)
    # العمود المركزي
    pole_width = int(size * 0.08)
    pole_height = int(size * 0.4)
    draw.rectangle([center_x - pole_width//2, center_y - pole_height,
                    center_x + pole_width//2, center_y], fill=color)
    # الكفة اليمنى (دائرة)
    right_pan_x = center_x + bar_width//2 - int(size*0.05)
    right_pan_y = center_y + bar_height//2
    draw.ellipse([right_pan_x - int(size*0.12), right_pan_y,
                  right_pan_x + int(size*0.12), right_pan_y + int(size*0.12)], fill=color)
    # الكفة اليسرى
    left_pan_x = center_x - bar_width//2 + int(size*0.05)
    draw.ellipse([left_pan_x - int(size*0.12), right_pan_y,
                  left_pan_x + int(size*0.12), right_pan_y + int(size*0.12)], fill=color)

# ================== إنشاء الأيقونة ==================
# 1. خلفية بتدرج لوني
img = create_gradient_image(SIZE, SIZE, COLOR_GRADIENT_START, COLOR_GRADIENT_END)
img = add_shadow(img, offset=10, blur=15)  # ظل خارجي

# 2. إضافة إطار ذهبي رفيع
draw = ImageDraw.Draw(img)
border_margin = int(SIZE * 0.05)
draw.rectangle([border_margin, border_margin, SIZE - border_margin, SIZE - border_margin],
               outline=COLOR_ACCENT, width=int(SIZE * 0.02))

# 3. رسم رمز الميزان في المنتصف
center_x, center_y = SIZE // 2, SIZE // 2
symbol_size = int(SIZE * 0.45)  # حجم رمز الميزان
draw_scales(draw, center_x, center_y, symbol_size, COLOR_ACCENT)

# 4. كتابة حرف "ر" أو اسم التطبيق
try:
    # محاولة استخدام خط عربي جميل (يمكنك تغيير المسار حسب نظامك)
    font_paths = [
        "/usr/share/fonts/truetype/tajawal/Tajawal-Bold.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf"
    ]
    font_path = None
    for fp in font_paths:
        if os.path.exists(fp):
            font_path = fp
            break
    if font_path:
        font = ImageFont.truetype(font_path, int(SIZE * 0.3))
    else:
        font = ImageFont.load_default()
except:
    font = ImageFont.load_default()

# رسم حرف "ر" أسفل رمز الميزان مباشرة (أو في المنتصف حسب التصميم)
text = "الراجحي"  # يمكن تغييره إلى "ر" أو "الراجحي"
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]
text_x = center_x - text_width // 2
text_y = center_y + symbol_size // 2 + int(SIZE * 0.05)
draw.text((text_x, text_y), text, fill=COLOR_ACCENT, font=font)

# 5. (اختياري) إضافة نجمة أو رمز صغير في الزاوية
star_size = int(SIZE * 0.07)
star_x = SIZE - border_margin - star_size
star_y = border_margin
draw.polygon([(star_x, star_y - star_size),
              (star_x + star_size*0.224, star_y - star_size*0.3),
              (star_x + star_size, star_y),
              (star_x + star_size*0.224, star_y + star_size*0.3),
              (star_x, star_y + star_size),
              (star_x - star_size*0.224, star_y + star_size*0.3),
              (star_x - star_size, star_y),
              (star_x - star_size*0.224, star_y - star_size*0.3)],
             fill=COLOR_ACCENT)

# ================== حفظ الأيقونة بأحجام متعددة ==================
# قياسات الأيقونة المطلوبة لملف ICO
sizes = [16, 24, 32, 48, 64, 128, 256, 512]

# إنشاء نسخة مصغرة لكل حجم وإضافتها إلى القائمة
icon_images = []
for sz in sizes:
    resized = img.resize((sz, sz), Image.LANCZOS)
    icon_images.append(resized)

# حفظ كملف ICO متعدد الأحجام
icon_images[0].save(OUTPUT_ICO, format='ICO', sizes=[(sz, sz) for sz in sizes], append_images=icon_images[1:])
print(f"✅ أيقونة ICO تم إنشاؤها: {OUTPUT_ICO} (يشمل {len(sizes)} حجمًا)")

# حفظ نسخة PNG عالية الجودة
img.save(OUTPUT_PNG, format='PNG')
print(f"✅ شعار PNG تم إنشاؤه: {OUTPUT_PNG}")

# ================== إنشاء ملف .rc لدمج الأيقونة مع exe (اختياري) ==================
rc_content = f"""IDI_ICON1 ICON DISCARDABLE "{OUTPUT_ICO}"
"""
with open("alrajhi_icon.rc", "w") as rc_file:
    rc_file.write(rc_content)
print("✅ تم إنشاء ملف alrajhi_icon.rc (للاستخدام مع PyInstaller أو Resource Hacker)")

# ================== نصائح إضافية ==================
print("\n🔹 لاستخدام الأيقونة في PyInstaller:")
print(f'   pyinstaller --onefile --windowed --icon="{OUTPUT_ICO}" --name "AlrajhiAccounting" main_pyqt5.py')
print("\n🔹 لإضافة الأيقونة داخل واجهة التطبيق:")
print('   self.setWindowIcon(QIcon("alrajhi_icon.ico"))')
