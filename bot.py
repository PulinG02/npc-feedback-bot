import os
import logging
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ── LOGGING ──────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── ENV ──────────────────────────────────────────────────
BOT_TOKEN = "8203041637:AAGagssGEzkwZ46wNnkVwUPECAcxu0xrs68"
FORWARD_ID = -1003991145962

# ── STATES ───────────────────────────────────────────────
RATING, CATEGORY, MESSAGE, PHOTO = range(4)

# ── KEYBOARDS ────────────────────────────────────────────
RATING_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("⭐ 1", callback_data="r1"),
        InlineKeyboardButton("⭐ 2", callback_data="r2"),
        InlineKeyboardButton("⭐ 3", callback_data="r3"),
        InlineKeyboardButton("⭐ 4", callback_data="r4"),
        InlineKeyboardButton("⭐ 5", callback_data="r5"),
    ]
])

CATEGORY_KB = InlineKeyboardMarkup([
    [InlineKeyboardButton("🐛 Bug Report",          callback_data="cBug Report")],
    [InlineKeyboardButton("💡 Feature Request",     callback_data="cFeature Request")],
    [InlineKeyboardButton("🔑 Key / License Issue", callback_data="cKey / License Issue")],
    [InlineKeyboardButton("💬 General",             callback_data="cGeneral")],
    [InlineKeyboardButton("📦 Other",               callback_data="cOther")],
])

SKIP_KB = ReplyKeyboardMarkup(
    [["⏭ Skip Photo"]], resize_keyboard=True, one_time_keyboard=True
)

STARS = {1:"★☆☆☆☆", 2:"★★☆☆☆", 3:"★★★☆☆", 4:"★★★★☆", 5:"★★★★★"}

# ── /start → straight to rating ──────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text(
        "👋 *Welcome to NPC Feedback Bot!*\n\n"
        "Your feedback helps us improve the NPC ecosystem.\n\n"
        "⭐ *How would you rate your experience?*",
        parse_mode="Markdown",
        reply_markup=RATING_KB
    )
    return RATING

# ── STEP 1: RATING ───────────────────────────────────────
async def get_rating(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    rating = int(query.data[1])
    ctx.user_data["rating"] = rating
    await query.edit_message_text(
        f"You rated: *{STARS[rating]}* ({rating}/5)\n\n"
        "🏷 *What is this feedback about?*",
        parse_mode="Markdown",
        reply_markup=CATEGORY_KB
    )
    return CATEGORY

# ── STEP 2: CATEGORY ─────────────────────────────────────
async def get_category(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data[1:]
    ctx.user_data["category"] = category
    await query.edit_message_text(
        f"Category: *{category}* ✅\n\n"
        "💬 *Please write your feedback message:*",
        parse_mode="Markdown"
    )
    return MESSAGE

# ── STEP 3: MESSAGE ───────────────────────────────────────
async def get_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["message"] = update.message.text.strip()
    await update.message.reply_text(
        "📸 *Got it!*\n\n"
        "Want to attach a screenshot?\n"
        "_Send a photo, or tap_ *⏭ Skip Photo* _to finish._",
        parse_mode="Markdown",
        reply_markup=SKIP_KB
    )
    return PHOTO

# ── STEP 4a: PHOTO ────────────────────────────────────────
async def get_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["photo_id"] = update.message.photo[-1].file_id
    await update.message.reply_text(
        "📎 Photo attached! Sending feedback...",
        reply_markup=ReplyKeyboardRemove()
    )
    return await finish(update, ctx)

# ── STEP 4b: SKIP PHOTO ───────────────────────────────────
async def skip_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["photo_id"] = None
    await update.message.reply_text(
        "Sending feedback...",
        reply_markup=ReplyKeyboardRemove()
    )
    return await finish(update, ctx)

# ── FINISH ────────────────────────────────────────────────
async def finish(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d        = ctx.user_data
    rating   = d.get("rating", 0)
    category = d.get("category", "General")
    message  = d.get("message", "")
    photo_id = d.get("photo_id")
    tg_user  = update.effective_user

    display_name = f"@{tg_user.username}" if tg_user.username else tg_user.first_name

    caption = (
        f"📬 <b>NEW FEEDBACK</b>\n\n"
        f"👤 <b>From:</b> {display_name} (<code>{tg_user.id}</code>)\n"
        f"⭐ <b>Rating:</b> {STARS[rating]} ({rating}/5)\n"
        f"🏷 <b>Category:</b> {category}\n\n"
        f"💬 <b>Message:</b>\n{message}\n\n"
        f"🕐 <i>{update.message.date.strftime('%Y-%m-%d %H:%M:%S UTC')}</i>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>NPC Feedback Bot</i>"
    )

    try:
        if photo_id:
            await ctx.bot.send_photo(
                chat_id=FORWARD_ID,
                photo=photo_id,
                caption=caption,
                parse_mode="HTML"
            )
        else:
            await ctx.bot.send_message(
                chat_id=FORWARD_ID,
                text=caption,
                parse_mode="HTML"
            )

        await update.message.reply_text(
            "✅ *Feedback sent successfully!*\n\n"
            "Thank you for helping improve the NPC ecosystem. 🙏\n\n"
            "Send /start to submit another feedback.",
            parse_mode="Markdown"
        )
        logger.info(f"Feedback from {tg_user.id} | Rating: {rating}/5 | {category}")

    except Exception as e:
        logger.error(f"Failed to forward: {e}")
        await update.message.reply_text(
            "❌ Something went wrong. Please try again.\n\nSend /start to retry."
        )

    ctx.user_data.clear()
    return ConversationHandler.END

# ── CANCEL ────────────────────────────────────────────────
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text(
        "❌ Feedback cancelled.\n\nSend /start anytime to try again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ── MAIN ──────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            RATING: [
                CallbackQueryHandler(get_rating, pattern=r"^r[1-5]$"),
            ],
            CATEGORY: [
                CallbackQueryHandler(get_category, pattern=r"^c"),
            ],
            MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_message),
            ],
            PHOTO: [
                MessageHandler(filters.PHOTO, get_photo),
                MessageHandler(filters.Regex(r"^⏭"), skip_photo),
                CommandHandler("skip", skip_photo),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)

    port        = int(os.environ.get("PORT", 8443))
    webhook_url = os.environ.get("WEBHOOK_URL", "")

    if webhook_url:
        logger.info(f"Starting webhook on port {port}")
        app.run_webhook(listen="0.0.0.0", port=port, webhook_url=webhook_url)
    else:
        logger.info("Starting polling (no WEBHOOK_URL set)")
        app.run_polling()

if __name__ == "__main__":
    main()
