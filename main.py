import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import asyncio

# ==================== الإعدادات الأساسية ====================
TOKEN = "8260723411:AAGDobfEt5SeuAEltqsZ-pqXIHP9_AgLk9w"  # ضع توكن البوت هنا

# إعدادات التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تخزين مؤقت للعمليات (لكل مستخدم)
user_sessions = {}

# ==================== إعدادات Selenium ====================

def create_driver():
    """إنشاء متصفح Chrome مع الإعدادات المناسبة"""
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # للعمل على السيرفرات (إذا شغلت البوت على استضافة)
    chrome_options.add_argument("--headless=new")  # شيل هذه إذا تبي تشوف المتصفح
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def create_gmail_account(first_name, desired_email, password):
    """
    دالة إنشاء حساب Gmail باستخدام Selenium
    ترجع: (نجاح/فشل, رسالة, الإيميل الكامل)
    """
    driver = None
    try:
        driver = create_driver()
        
        # الذهاب لصفحة التسجيل
        logger.info("جاري فتح صفحة التسجيل...")
        driver.get("https://accounts.google.com/signup")
        time.sleep(3)
        
        # ===== الخطوة 1: الاسم =====
        logger.info("جاري إدخال الاسم...")
        
        # انتظار حقل الاسم الأول
        first_name_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "firstName"))
        )
        first_name_field.send_keys(first_name)
        
        # حقل الاسم الأخير (نحطه نفس الأول أو نتركه فارغ)
        last_name_field = driver.find_element(By.ID, "lastName")
        last_name_field.send_keys(first_name)  # أو حط lastName برضه
        
        # زر التالي
        next_button = driver.find_element(By.XPATH, "//span[text()='Next']")
        next_button.click()
        time.sleep(3)
        
        # ===== الخطوة 2: تاريخ الميلاد والجنس =====
        logger.info("جاري إدخال تاريخ الميلاد...")
        
        # شهر (نحط قيمة افتراضية)
        month_field = driver.find_element(By.ID, "month")
        month_field.send_keys("January")
        
        # يوم
        day_field = driver.find_element(By.ID, "day")
        day_field.send_keys("15")
        
        # سنة
        year_field = driver.find_element(By.ID, "year")
        year_field.send_keys("1990")
        
        # الجنس (نختار ذكر)
        gender_field = driver.find_element(By.ID, "gender")
        gender_field.send_keys("Male")
        
        # زر التالي
        next_button = driver.find_element(By.XPATH, "//span[text()='Next']")
        next_button.click()
        time.sleep(3)
        
        # ===== الخطوة 3: اختيار اسم المستخدم =====
        logger.info("جاري اختيار اسم المستخدم...")
        
        # نضغط على "Create your own Gmail address"
        try:
            create_own = driver.find_element(By.XPATH, "//span[contains(text(),'Create your own')]")
            create_own.click()
            time.sleep(2)
        except:
            pass  # يمكن تكون الصفحة مختلفة
        
        # حقل اسم المستخدم
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "Username"))
        )
        username_field.clear()
        username_field.send_keys(desired_email)
        
        # زر التالي
        next_button = driver.find_element(By.XPATH, "//span[text()='Next']")
        next_button.click()
        time.sleep(3)
        
        # التحقق إذا كان الاسم محجوز
        page_source = driver.page_source
        if "That username is taken" in page_source or "not available" in page_source:
            return False, "اسم المستخدم هذا محجوز، جرب اسماً آخر", None
        
        # ===== الخطوة 4: كلمة السر =====
        logger.info("جاري إدخال كلمة السر...")
        
        # حقل كلمة السر
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "Passwd"))
        )
        password_field.send_keys(password)
        
        # تأكيد كلمة السر
        confirm_field = driver.find_element(By.NAME, "PasswdAgain")
        confirm_field.send_keys(password)
        
        # زر التالي
        next_button = driver.find_element(By.XPATH, "//span[text()='Next']")
        next_button.click()
        time.sleep(5)
        
        # ===== هنا راح يطلب رقم هاتف للتحقق =====
        # هذه هي المشكلة: Google تطلب رقم هاتف
        page_source = driver.page_source
        if "phoneNumber" in page_source or "Phone number" in page_source:
            return False, "Google تطلب رقم هاتف للتحقق. البوت لا يدعم التحقق الهاتفي بعد.", None
        
        # إذا نجحنا
        email = f"{desired_email}@gmail.com"
        return True, f"✅ تم إنشاء الحساب بنجاح!\n📧 الإيميل: {email}\n🔑 كلمة السر: {password}", email
        
    except Exception as e:
        logger.error(f"خطأ في إنشاء الحساب: {str(e)}")
        return False, f"❌ حدث خطأ: {str(e)}", None
    
    finally:
        if driver:
            driver.quit()

# ==================== معالجي البوت ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب"""
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name
    
    welcome_text = f"""
🎉 **مرحباً بك {username} في بوت إنشاء Gmail!**

📧 **هذا البوت يساعدك في إنشاء حساب Gmail جديد.**

📝 **طريقة الاستخدام:**
أرسل لي البيانات بهذا الشكل:

`الاسم الأول | اسم الإيميل | كلمة السر`

✅ **مثال:**
`أحمد | ahmed123 | MyPassword123`

⚠️ **ملاحظات مهمة:**
• Google تطلب رقم هاتف للتحقق في بعض الحالات
• قد لا ينجح الإنشاء إذا كان الإيميل محجوز
• استخدم كلمة سر قوية (حروف وأرقام)

⚙️ اختر من الأزرار تحت:
"""
    
    keyboard = [
        [
            InlineKeyboardButton("📧 إنشاء حساب", callback_data="create"),
            InlineKeyboardButton("ℹ️ مساعدة", callback_data="help")
        ],
        [
            InlineKeyboardButton("👤 مطور البوت", url="https://t.me/SI123FO")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية (البيانات)"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # التحقق من الصيغة: اسم | ايميل | كلمة سر
    pattern = r'^(.+?)\s*\|\s*(.+?)\s*\|\s*(.+)$'
    match = re.match(pattern, text)
    
    if not match:
        await update.message.reply_text(
            "❌ **صيغة خاطئة!**\n\n"
            "أرسل البيانات بهذا الشكل:\n"
            "`الاسم الأول | اسم الإيميل | كلمة السر`\n\n"
            "مثال: `أحمد | ahmed123 | MyPassword123`"
        )
        return
    
    first_name = match.group(1).strip()
    desired_email = match.group(2).strip()
    password = match.group(3).strip()
    
    # تحقق بسيط من كلمة السر
    if len(password) < 8:
        await update.message.reply_text("❌ كلمة السر قصيرة جداً! استخدم 8 أحرف على الأقل.")
        return
    
    # رسالة انتظار
    status_msg = await update.message.reply_text(
        f"🔄 جاري إنشاء الحساب...\n"
        f"الاسم: {first_name}\n"
        f"الإيميل المطلوب: {desired_email}@gmail.com\n"
        f"يرجى الانتظار (قد يستغرق 2-3 دقائق)"
    )
    
    # تشغيل عملية الإنشاء في Thread منفصل عشان لا نوقف البوت
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None, 
        create_gmail_account, 
        first_name, desired_email, password
    )
    
    success, message, email = result
    
    if success:
        await status_msg.edit_text(message)
    else:
        await status_msg.edit_text(message)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "create":
        await query.edit_message_text(
            "📧 **إنشاء حساب Gmail جديد**\n\n"
            "أرسل لي البيانات بهذا الشكل:\n\n"
            "`الاسم الأول | اسم الإيميل | كلمة السر`\n\n"
            "مثال: `محمد | mohamed123 | MyPass@2025`"
        )
    
    elif data == "help":
        help_text = """
ℹ️ **مساعدة البوت**

📌 **كيفية الاستخدام:**
1. أرسل البيانات بالصيغة: `الاسم | الإيميل | كلمة السر`
2. البوت يبدأ في إنشاء الحساب (يستغرق 2-3 دقائق)
3. استلم نتيجة الإنشاء

⚠️ **ملاحظات مهمة:**
• Google تطلب رقم هاتف في بعض الأحيان
• إذا طلب رقم هاتف، العملية تفشل
• تأكد أن الإيميل غير محجوز
• استخدم كلمة سر قوية (حروف كبيرة وصغيرة + أرقام)

👤 مطور البوت: @SI123FO
"""
        await query.edit_message_text(help_text, parse_mode='Markdown')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الأخطاء"""
    logger.error(f"حدث خطأ: {context.error}")

# ==================== تشغيل البوت ====================

def main():
    """تشغيل البوت"""
    
    application = Application.builder().token(TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    
    print("✅ بوت إنشاء Gmail يعمل...")
    print("👤 يوزر المطور: @SI123FO")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
