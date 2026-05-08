import time
import requests
import asyncio
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

API_URL = "https://adhahi.dz/api/v1/public/wilaya-quotas"
BOT_TOKEN = "8407646122:AAFI7obTC8f9ijkUDYdofxNBwfPrSHptB8Q"
CHAT_ID = "858975589"
TARGET_WILAYA = "34"
CHECK_EVERY_SECONDS = 60

bot = Bot(token=BOT_TOKEN)


async def fetch_wilaya_status():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://adhahi.dz/"
    }
    response = requests.get(API_URL, headers=headers, timeout=15)
    data = response.json()
    for w in data:
        if w["wilayaCode"] == TARGET_WILAYA:
            return w["wilayaNameAr"], w["available"]
    return None, None


async def send_status_check(chat_id=CHAT_ID):
    try:
        name, available = await fetch_wilaya_status()
        if name is None:
            await bot.send_message(chat_id=chat_id, text="⚠️ لم يتم العثور على الولاية.")
            return

        status_icon = "🟢 متاح الآن" if available else "🔴 غير متاح حالياً"
        message = f"""
📡 <b>فحص يدوي</b>

🏷 <b>الولاية:</b> {name}
🔢 <b>الرمز:</b> {TARGET_WILAYA}
📊 <b>الحالة:</b> {status_icon}

🕐 <b>وقت الفحص:</b> {time.strftime("%H:%M:%S")}
"""
        زر = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 فحص مجدداً", callback_data="recheck")]
        ])
        await bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML", reply_markup=زر)

    except Exception as e:
        await bot.send_message(chat_id=chat_id, text=f"⚠️ خطأ أثناء الفحص:\n{e}")
        print("خطأ:", e)


async def check_wilaya():
    name, available = await fetch_wilaya_status()
    if name is None:
        return
    if available:
        message = f"""
🚨 <b>تنبيه عاجل - متاح الآن</b>

🏷 <b>الولاية:</b> {name}
🔢 <b>الرمز:</b> {TARGET_WILAYA}
🟢 <b>الحالة:</b> متاح الآن

⚡ سارع بالحجز قبل فوات الأوان!
"""
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")
        print(f"تم إرسال التنبيه: {name} ← متاح")
    else:
        print(f"{name} ← غير متاح")


async def monitor_loop():
    print("بدأت المراقبة...")
    while True:
        try:
            await check_wilaya()
        except Exception as e:
            print("خطأ في المراقبة:", e)
        await asyncio.sleep(CHECK_EVERY_SECONDS)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    زر = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 فحص الحالة الآن", callback_data="recheck")]
    ])
    await update.message.reply_text(
        "👋 <b>أهلاً وسهلاً!</b>\n\nاضغط على الزر أدناه لمعرفة حالة توفر الأضاحي في ولايتك فوراً.",
        parse_mode="HTML",
        reply_markup=زر
    )


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text("⏳ جاري الفحص، لحظة من فضلك...")
    await send_status_check(chat_id=chat_id)


async def callback_recheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("⏳ جاري الفحص...")
    await send_status_check(chat_id=query.message.chat_id)


async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CallbackQueryHandler(callback_recheck, pattern="^recheck$"))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    try:
        await monitor_loop()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


asyncio.run(main())