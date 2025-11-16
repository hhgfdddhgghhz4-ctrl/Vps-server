import logging
import asyncio
import random
import string
import time
from datetime import datetime
import aiohttp
import requests
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
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
TOKEN = "YOUR_BOT_TOKEN_HERE"  # ضع توكن البوت بتاعك هنا
OWNER_ID = 123456789  # ضع يور ID بتاعك هنا عشان تبقى أونر

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
    "udp_flood": {
        "name": "💥 UDP Flood",
        "description": "فيضان حزم UDP عشوائي",
        "ports": [53, 80, 443, 8080],
    },
    "tcp_ack": {
        "name": "🔥 TCP ACK Flood",
        "description": "هجوم TCP ACK لتجاوز الجدران النارية",
        "ports": [80, 443, 22, 21],
    },
}

# --- قاعدة بيانات بسيطة (في الذاكرة) ---
owners = set([OWNER_ID])
approved_users = set()  # المستخدمين اللي تمت الموافقة عليهم
pending_users = set()  # المستخدمين اللي مستنيين موافقة
attack_sessions = {}  # عشان نتابع الهجمات اللي شغالة

# --- تسجيل الأحداث (Logging) ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --- دوال مساعدة ---
def is_owner(user_id: int) -> bool:
    """تتحقق إذا كان المستخدم أونر"""
    return user_id in owners


async def is_valid_target(target: str) -> bool:
    """تحقق بسيط إذا كان الهدف IP أو رابط صحيح"""
    if target.replace(".", "").replace(":", "").replace("-", "").replace("/", "").isalnum():
        return True
    return False


# --- دوال الهجوم (هتكون محاكاة هنا) ---
async def execute_attack(target: str, port: int, method: str, duration: int, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """
    هنا هتحط منطق الهجوم الفعلي.
    ده مجرد مثال، لازم تستخدم مكتبات متخصصة زي socket, aiohttp, asyncio
    """
    session_id = random.randint(10000, 99999)
    logger.info(f"🚀 بدء الهجوم #{session_id} على {target}:{port} باستخدام {method} لمدة {duration} ثانية")
    
    # --- هنا بداية منطق الهجوم الفعلي ---
    # مثال لـ Slowloris
    if method == "slowloris":
        # استدعاء دالة Slowloris الفعلية
        pass
    elif method == "http2_rapid":
        # استدعاء دالة HTTP/2 Rapid Reset
        pass
    # وهكذا...
    # --- نهاية منطق الهجوم الفعلي ---

    # محاكاة مرور الوقت
    for i in range(duration):
        await asyncio.sleep(1)
        # ممكن هنا تبعت تحديثات كل 10 ثواني مثلاً
        if i > 0 and i % 10 == 0:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔄 الهجوم #{session_id} مستمر... ({i}/{duration} ثانية)"
            )

    logger.info(f"✅ انتهى الهجوم #{session_id}")
    return session_id


# --- معالجات الأوامر والأزرار ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عندما يبدأ المستخدم البوت"""
    user = update.effective_user
    user_id = user.id
    
    # لو المستخدم أونر
    if is_owner(user_id):
        keyboard = [
            [
                InlineKeyboardButton("🎯 بدء هجوم جديد", callback_data="new_attack"),
                InlineKeyboardButton("📊 حالة الهجمات", callback_data="attack_status"),
            ],
            [
                InlineKeyboardButton("👥 طلبات الانضمام", callback_data="pending_requests"),
                InlineKeyboardButton("⚙️ إعدادات البوت", callback_data="bot_settings"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"مرحباً {user.first_name}!\n\n👑 **لوحة تحكم الأونر**",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return

    # لو المستخدم مواف عليه بالفعل
    if user_id in approved_users:
        keyboard = [
            [
                InlineKeyboardButton("🚀 بدء هجوم", callback_data="new_attack"),
                InlineKeyboardButton("📊 حالة الهجمات", callback_data="attack_status"),
            ],
            [InlineKeyboardButton("ℹ️ معلومات", callback_data="info")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"مرحباً بك {user.first_name}!\n\nاختر من الأزرار:",
            reply_markup=reply_markup
        )
        return

    # لو مستخدم جديد أو مستني موافقة
    if user_id not in pending_users:
        pending_users.add(user_id)
        
        # إرسال إشعار للأونر
        if owners:
            owner_id = next(iter(owners))
            approval_keyboard = [
                [
                    InlineKeyboardButton("✅ موافق", callback_data=f"approve_{user_id}"),
                    InlineKeyboardButton("❌ ارفض", callback_data=f"reject_{user_id}"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(approval_keyboard)
            
            await context.bot.send_message(
                chat_id=owner_id,
                text=(
                    f"🔔 **طلب انضمام جديد**\n\n"
                    f"👤 الاسم: {user.first_name}\n"
                    f"🆔 اليوزر ID: `{user_id}`\n"
                    f"👀 يوزرنيم: @{user.username if user.username else 'N/A'}\n\n"
                    "وافق أو ارفض طلب الانضمام:"
                ),
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
    
    # رسالة للمستخدم إنه مستني الموافقة
    await update.message.reply_text(
        "👋 مرحباً!\n\n"
        "طلب انضمامك تم إرساله للأونر.\n"
        "يرجى الانتظار حتى تتم مراجعة طلبك.\n\n"
        "⏳ ستصل إشعار هنا بمجرد اتخاذ القرار."
    )


async def approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج موافقة أو رفض طلب الانضمام"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # تأكد إن اللي ضغط على الزر أونر
    if not is_owner(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية للقيام بذلك!")
        return
    
    data = query.data
    parts = data.split("_")
    action = parts[0]
    target_user_id = int(parts[1])
    
    try:
        target_user = await context.bot.get_chat(target_user_id)
        target_name = target_user.first_name
    except:
        target_name = "مستخدم"
    
    if action == "approve":
        approved_users.add(target_user_id)
        if target_user_id in pending_users:
            pending_users.remove(target_user_id)
        
        await query.edit_message_text(
            f"✅ **تمت الموافقة** على طلب الانضمام لـ {target_name} (`{target_user_id}`)",
            parse_mode="Markdown"
        )
        
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                "🎉 **تهانينا!\n\n"
                "تمت الموافقة على طلب انضمامك.\n"
                "الآن يمكنك استخدام البوت.\n\n"
                "أرسل /start لبدء استخدام البوت."
            ),
            parse_mode="Markdown"
        )
        
    elif action == "reject":
        if target_user_id in pending_users:
            pending_users.remove(target_user_id)
        
        await query.edit_message_text(
            f"❌ **تم الرفض** على طلب الانضمام لـ {target_name} (`{target_user_id}`)",
            parse_mode="Markdown"
        )
        
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                "😔 **نأسى لذلك!\n\n"
                "تم رفض طلب انضمامك للبوت.\n"
                "لديك الحق في التقديم مرة أخرى في وقت لاحق."
            ),
            parse_mode="Markdown"
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج ضغطات الأزرار العامة"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "new_attack" and (is_owner(user_id) or user_id in approved_users):
        await query.edit_message_text(
            "أرسل الآن الهدف (IP أو رابط):\n\n"
            "مثال: 192.168.1.1 أو https://example.com"
        )
        
    elif data == "attack_status" and is_owner(user_id):
        status_text = "📊 **حالة الهجمات الحالية:**\n\n"
        if not attack_sessions:
            status_text += "لا توجد هجمات شغالة حالياً."
        else:
            for sid, session in attack_sessions.items():
                elapsed = (datetime.now() - session['start_time']).total_seconds()
                status_text += (
                    f"🆔 الهجوم: `{sid}`\n"
                    f"🎯 الهدف: `{session['target']}`\n"
                    f"⚡ الطريقة: {ATTACK_METHODS[session['method']]['name']}\n"
                    f"⏱️ مضى: {int(elapsed)} ثانية\n\n"
                )
        await query.edit_message_text(status_text, parse_mode="Markdown")
        
    elif data == "pending_requests" and is_owner(user_id):
        requests_text = "👥 **طلبات الانضمام المنتظرة:**\n\n"
        if not pending_users:
            requests_text += "لا توجد طلبات منتظرة."
        else:
            for uid in list(pending_users):
                requests_text += f"🆔 `{uid}`\n"
        await query.edit_message_text(requests_text, parse_mode="Markdown")

    elif data == "info":
        info_text = (
            "🤖 **معلومات البوت**\n\n"
            "الإصدار: 2.0\n"
            "المطور: Blackhatsense\n\n"
            "التقنيات المتاحة:\n"
        )
        for method_key, method_info in ATTACK_METHODS.items():
            info_text += f"- {method_info['name']}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(info_text, reply_markup=reply_markup)
        
    elif data == "back_to_main":
        # نعيد إرسال رسالة /start عشان نرجع للوحة التحكم
        # لسه بنعمل update.message.reply_text فمش هينفع، محتاجين نعمل context.bot.send_message
        # لسه بنستخدم update.callback_query.message.chat_id
        await start(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل النصية"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # لو الأونر أو المستخدم المواف عليه بعت هدف
    if is_owner(user_id) or user_id in approved_users:
        if await is_valid_target(text):
            # عرض طرق الهجوم المتاحة
            keyboard = []
            for method_key, method_info in ATTACK_METHODS.items():
                keyboard.append([
                    InlineKeyboardButton(
                        f"{method_info['name']}",
                        callback_data=f"attack_{method_key}_{text}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 إلغاء", callback_data="back_to_main")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"تم تحديد الهدف: `{text}`\n\n"
                "اختر طريقة الهجوم:",
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ هدف غير صالح. حاول مرة أخرى.")


async def attack_method_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج اختيار طريقة الهجوم"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("attack_"):
        parts = data.split("_", 2)
        method = parts[1]
        target = parts[2]
        
        keyboard = [
            [
                InlineKeyboardButton("60 ثانية", callback_data=f"duration_{target}_{method}_60"),
                InlineKeyboardButton("120 ثانية", callback_data=f"duration_{target}_{method}_120"),
                InlineKeyboardButton("300 ثانية", callback_data=f"duration_{target}_{method}_300"),
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"الهدف: `{target}`\n"
            f"الطريقة: {ATTACK_METHODS[method]['name']}\n\n"
            "اختر مدة الهجوم:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )


async def duration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج اختيار مدة الهجوم وبدء الهجوم الفعلي"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("duration_"):
        parts = data.split("_", 3)
        target = parts[1]
        method = parts[2]
        duration = int(parts[3])
        
        session_id = random.randint(10000, 99999)
        
        # حفظ الهجوم في القاعدة
        attack_sessions[session_id] = {
            "target": target,
            "method": method,
            "duration": duration,
            "start_time": datetime.now(),
        }
        
        await query.edit_message_text(
            f"🚀 **بدأ الهجوم بنجاح!**\n\n"
            f"🎯 الهدف: `{target}`\n"
            f"⚡ الطريقة: {ATTACK_METHODS[method]['name']}\n"
            f"⏱️ المدة: {duration} ثانية\n"
            f"🆔 رقم الهجوم: `{session_id}`\n\n"
            "سيتم إعلامك عند الانتهاء.",
            parse_mode="Markdown"
        )
        
        # بدء الهجوم في الخلفية
        attack_task = asyncio.create_task(
            execute_attack(target, 80, method, duration, context, query.from_user.id)
        )
        
        # انتظر حتى ينتهي الهجوم وبعت إشعار
        try:
            final_session_id = await attack_task
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=f"✅ **انتهى الهجوم #{final_session_id}** بنجاح."
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=f"❌ **حدث خطأ في الهجوم #{session_id}**: {e}"
            )
        finally:
            if session_id in attack_sessions:
                del attack_sessions[session_id]


def main():
    """دالة تشغيل البوت الرئيسية"""
    application = Application.builder().token(TOKEN).build()
    
    # معالجات الأوامر
    application.add_handler(CommandHandler("start", start))
    
    # معالجات الأزرار (الترتيب مهم!)
    # 1. معالج الموافقة/الرفض (الأكثر تحديدًا)
    application.add_handler(CallbackQueryHandler(approval_callback, pattern="^(approve|reject)_"))
    # 2. معالج اختيار طريقة الهجوم
    application.add_handler(CallbackQueryHandler(attack_method_callback, pattern="^attack_"))
    # 3. معالج اختيار مدة الهجوم
    application.add_handler(CallbackQueryHandler(duration_callback, pattern="^duration_"))
    # 4. المعالج العام للأزرار
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # معالج الرسائل النصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # تشغيل البوت
    logger.info("🚀 بدء تشغيل بوت DDOS...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
