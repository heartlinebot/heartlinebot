import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from database import Database
from scheduler import MessageScheduler
from ai_generator import generate_message
from weather import get_weather

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

(MAIN_MENU, ADD_RECIPIENT_NAME, ADD_RECIPIENT_RELATION, ADD_RECIPIENT_CONTACT,
 ADD_RECIPIENT_TONE, ADD_RECIPIENT_SCHEDULE, ADD_RECIPIENT_SCHEDULE_TIME,
 SET_CITY, SET_SEND_MODE, PREVIEW_CONFIRM) = range(10)

db = Database()
scheduler = MessageScheduler()

RELATIONS = {
    "mama":     "💙 Мама",
    "tato":     "💪 Тато",
    "druzhyna": "❤️ Дружина/Чоловік",
    "brat":     "🤝 Брат/Сестра",
    "druh":     "😊 Друг/Подруга",
    "babusya":  "🌸 Бабуся/Дідусь",
    "syn":      "👦 Син",
    "dochka":   "👧 Донька",
    "kolega":   "🤝 Колега",
}

TONES = {
    "warm":     "🤗 Тепло і турботливо",
    "funny":    "😄 Весело і з гумором",
    "romantic": "💕 Романтично",
    "calm":     "🕊 Спокійно",
    "neutral":  "📝 Нейтрально",
}

DAYS_UK = {
    "mon": "Пн", "tue": "Вт", "wed": "Ср",
    "thu": "Чт", "fri": "Пт", "sat": "Сб", "sun": "Нд"
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.save_user(user.id, user.first_name, user.username)
    text = (
        f"👋 Привіт, {user.first_name}!\n\n"
        "Я — *HeartLine* 💌\n"
        "Надсилаю теплі повідомлення твоїм рідним автоматично.\n\n"
        "Обери, що хочеш зробити:"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())
    return MAIN_MENU


def main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Мої одержувачі", callback_data="list_recipients")],
        [InlineKeyboardButton("➕ Додати одержувача", callback_data="add_recipient")],
        [InlineKeyboardButton("🌍 Моє місто", callback_data="set_city")],
        [InlineKeyboardButton("⚙️ Режим надсилання", callback_data="set_mode")],
        [InlineKeyboardButton("📨 Надіслати зараз (тест)", callback_data="send_now")],
    ])


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "list_recipients":
        return await show_recipients(update, context)
    elif data == "add_recipient":
        return await add_recipient_start(update, context)
    elif data == "set_city":
        return await ask_city(update, context)
    elif data == "set_mode":
        return await show_send_mode(update, context)
    elif data == "send_now":
        return await send_now_handler(update, context)
    elif data == "back_main":
        await query.edit_message_text("Головне меню:", reply_markup=main_keyboard())
        return MAIN_MENU


async def show_recipients(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    recipients = db.get_recipients(user_id)
    if not recipients:
        text = "👥 У тебе ще немає одержувачів.\nДодай першого!"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Додати", callback_data="add_recipient")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
        ])
    else:
        text = "👥 *Твої одержувачі:*\n\n"
        buttons = []
        for r in recipients:
            relation_label = RELATIONS.get(r['relation'], r['relation'])
            tone_label = TONES.get(r['tone'], r['tone'])
            text += f"{relation_label} — *{r['name']}*\n   Тон: {tone_label}\n   Розклад: {r.get('schedule_days','?')} о {r.get('schedule_time','?')}\n\n"
            buttons.append([InlineKeyboardButton(f"🗑 Видалити {r['name']}", callback_data=f"del_{r['id']}")])
        buttons.append([InlineKeyboardButton("➕ Додати ще", callback_data="add_recipient")])
        buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
        kb = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    return MAIN_MENU


async def delete_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    recipient_id = int(query.data.split("_")[1])
    db.delete_recipient(recipient_id)
    await query.edit_message_text("✅ Одержувача видалено.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ До списку", callback_data="list_recipients")]
    ]))
    return MAIN_MENU


async def add_recipient_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    context.user_data.clear()
    await query.edit_message_text("➕ *Додаємо нового одержувача*\n\nЯк його/її звати?", parse_mode="Markdown")
    return ADD_RECIPIENT_NAME


async def add_recipient_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['rec_name'] = update.message.text.strip()
    buttons = [[InlineKeyboardButton(label, callback_data=f"rel_{key}")] for key, label in RELATIONS.items()]
    await update.message.reply_text(
        f"Чудово! Хто таке *{context.user_data['rec_name']}* для тебе?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return ADD_RECIPIENT_RELATION


async def add_recipient_relation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['rec_relation'] = query.data.replace("rel_", "")
    await query.edit_message_text(
        f"Як надіслати повідомлення *{context.user_data['rec_name']}*?\n\n"
        "Введи їх Telegram username (наприклад @username) або номер телефону (+380XXXXXXXXX):",
        parse_mode="Markdown"
    )
    return ADD_RECIPIENT_CONTACT


async def add_recipient_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['rec_contact'] = update.message.text.strip()
    buttons = [[InlineKeyboardButton(label, callback_data=f"tone_{key}")] for key, label in TONES.items()]
    await update.message.reply_text(
        f"Яким тоном писати *{context.user_data['rec_name']}*?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return ADD_RECIPIENT_TONE


async def add_recipient_tone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['rec_tone'] = query.data.replace("tone_", "")
    day_buttons = [[InlineKeyboardButton(label, callback_data=f"day_{key}")] for key, label in DAYS_UK.items()]
    day_buttons.append([InlineKeyboardButton("✅ Щодня", callback_data="day_everyday")])
    day_buttons.append([InlineKeyboardButton("✅ Готово", callback_data="days_done")])
    context.user_data['rec_days'] = []
    await query.edit_message_text(
        "📅 Які дні надсилати повідомлення?\nОбери дні і натисни «Готово»:",
        reply_markup=InlineKeyboardMarkup(day_buttons)
    )
    return ADD_RECIPIENT_SCHEDULE


async def add_recipient_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "days_done":
        if not context.user_data.get('rec_days'):
            context.user_data['rec_days'] = ['everyday']
        days_str = "Щодня" if 'everyday' in context.user_data['rec_days'] else ", ".join([DAYS_UK.get(d, d) for d in context.user_data['rec_days']])
        await query.edit_message_text(
            f"⏰ О котрій годині надсилати?\nДні: *{days_str}*\n\nВведи час у форматі HH:MM (наприклад 09:00):",
            parse_mode="Markdown"
        )
        return ADD_RECIPIENT_SCHEDULE_TIME
    day = query.data.replace("day_", "")
    if day == "everyday":
        context.user_data['rec_days'] = ['everyday']
    else:
        days = context.user_data.get('rec_days', [])
        if day in days:
            days.remove(day)
        else:
            days.append(day)
        context.user_data['rec_days'] = days
    selected = context.user_data.get('rec_days', [])
    day_buttons = []
    for key, label in DAYS_UK.items():
        mark = "✅ " if key in selected else ""
        day_buttons.append([InlineKeyboardButton(f"{mark}{label}", callback_data=f"day_{key}")])
    day_buttons.append([InlineKeyboardButton("✅ Щодня" if 'everyday' in selected else "Щодня", callback_data="day_everyday")])
    day_buttons.append([InlineKeyboardButton("✅ Готово", callback_data="days_done")])
    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(day_buttons))
    return ADD_RECIPIENT_SCHEDULE


async def add_recipient_schedule_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_text = update.message.text.strip()
    try:
        datetime.strptime(time_text, "%H:%M")
    except ValueError:
        await update.message.reply_text("❌ Невірний формат. Введи час як 09:00 або 18:30:")
        return ADD_RECIPIENT_SCHEDULE_TIME
    context.user_data['rec_time'] = time_text
    user_id = update.effective_user.id
    recipient_id = db.add_recipient(
        user_id=user_id,
        name=context.user_data['rec_name'],
        relation=context.user_data['rec_relation'],
        contact=context.user_data['rec_contact'],
        tone=context.user_data['rec_tone'],
        schedule_days=", ".join(context.user_data['rec_days']),
        schedule_time=time_text
    )
    scheduler.schedule_recipient(
        recipient_id=recipient_id,
        user_id=user_id,
        days=context.user_data['rec_days'],
        time_str=time_text,
        context=context
    )
    relation_label = RELATIONS.get(context.user_data['rec_relation'], '')
    tone_label = TONES.get(context.user_data['rec_tone'], '')
    days_str = "Щодня" if 'everyday' in context.user_data['rec_days'] else ", ".join([DAYS_UK.get(d, d) for d in context.user_data['rec_days']])
    await update.message.reply_text(
        f"✅ *Одержувача додано!*\n\n{relation_label} — *{context.user_data['rec_name']}*\n"
        f"🎭 Тон: {tone_label}\n📅 Розклад: {days_str} о {time_text}\n\nБуду надсилати автоматично 💌",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )
    return MAIN_MENU


async def ask_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.edit_message_text("🌍 Введи своє місто (наприклад: Київ, Берлін, Варшава):")
    return SET_CITY


async def save_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    db.update_user_city(update.effective_user.id, city)
    await update.message.reply_text(f"✅ Місто збережено: *{city}* 🌤", parse_mode="Markdown", reply_markup=main_keyboard())
    return MAIN_MENU


async def show_send_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = db.get_user(update.effective_user.id)
    current = user.get('send_mode', 'auto') if user else 'auto'
    modes = {
        "auto":    "🤖 Авто — без моєї участі",
        "preview": "👁 Показати перед надсиланням",
        "manual":  "✏️ Редагувати кожного разу",
    }
    buttons = []
    for key, label in modes.items():
        mark = "✅ " if key == current else ""
        buttons.append([InlineKeyboardButton(f"{mark}{label}", callback_data=f"mode_{key}")])
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    await query.edit_message_text("⚙️ *Режим надсилання:*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    return SET_SEND_MODE


async def save_send_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode = query.data.replace("mode_", "")
    db.update_send_mode(update.effective_user.id, mode)
    labels = {"auto": "🤖 Авто", "preview": "👁 Передперегляд", "manual": "✏️ Ручне"}
    await query.edit_message_text(
        f"✅ Режим збережено: *{labels.get(mode, mode)}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Головне меню", callback_data="back_main")]])
    )
    return MAIN_MENU


async def send_now_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    recipients = db.get_recipients(user_id)
    if not recipients:
        await query.edit_message_text("❌ Немає одержувачів.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➕ Додати", callback_data="add_recipient")]]))
        return MAIN_MENU
    buttons = [[InlineKeyboardButton(f"📨 {RELATIONS.get(r['relation'],'')} {r['name']}", callback_data=f"sendtest_{r['id']}")] for r in recipients]
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="back_main")])
    await query.edit_message_text("📨 *Кому надіслати зараз?*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
    return MAIN_MENU


async def send_test_to(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    recipient_id = int(query.data.split("_")[1])
    user_id = update.effective_user.id
    recipient = db.get_recipient(recipient_id)
    user = db.get_user(user_id)
    city = user.get('city', '') if user else ''
    weather_info = await get_weather(city) if city else ""
    message_text = await generate_message(
        recipient_name=recipient['name'],
        relation=recipient['relation'],
        tone=recipient['tone'],
        city=city,
        weather=weather_info
    )
    send_mode = user.get('send_mode', 'auto') if user else 'auto'
    if send_mode == 'preview':
        context.user_data['preview_text'] = message_text
        await query.edit_message_text(
            f"👁 *Попередній перегляд:*\n\n{message_text}\n\nНадіслати *{recipient['name']}*?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Надіслати", callback_data=f"confirm_send_{recipient_id}")],
                [InlineKeyboardButton("🔄 Інший варіант", callback_data=f"sendtest_{recipient_id}")],
                [InlineKeyboardButton("◀️ Скасувати", callback_data="back_main")],
            ])
        )
        return PREVIEW_CONFIRM
    else:
        success = await deliver_message(context, recipient, message_text)
        result = f"✅ Надіслано!\n\n_{message_text}_" if success else f"⚠️ Не вдалося надіслати.\n\nПовідомлення:\n_{message_text}_"
        await query.edit_message_text(result, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Меню", callback_data="back_main")]]))
        return MAIN_MENU


async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    recipient_id = int(query.data.split("_")[2])
    recipient = db.get_recipient(recipient_id)
    message_text = context.user_data.get('preview_text', '')
    success = await deliver_message(context, recipient, message_text)
    result = "✅ Надіслано!" if success else "⚠️ Помилка"
    await query.edit_message_text(f"{result}\n\n_{message_text}_", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Меню", callback_data="back_main")]]))
    return MAIN_MENU


async def deliver_message(context, recipient, text):
    try:
        contact = recipient['contact']
        if contact.startswith('@'):
            await context.bot.send_message(chat_id=contact, text=text)
            return True
        return False
    except Exception as e:
        logger.error(f"Delivery error: {e}")
        return False


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable not set!")
    app = Application.builder().token(token).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(main_menu_handler, pattern="^(list_recipients|add_recipient|set_city|set_mode|send_now|back_main)$"),
                CallbackQueryHandler(delete_recipient, pattern="^del_"),
                CallbackQueryHandler(send_test_to, pattern="^sendtest_"),
                CallbackQueryHandler(confirm_send, pattern="^confirm_send_"),
                CallbackQueryHandler(save_send_mode, pattern="^mode_"),
            ],
            ADD_RECIPIENT_NAME:          [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipient_name)],
            ADD_RECIPIENT_RELATION:      [CallbackQueryHandler(add_recipient_relation, pattern="^rel_")],
            ADD_RECIPIENT_CONTACT:       [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipient_contact)],
            ADD_RECIPIENT_TONE:          [CallbackQueryHandler(add_recipient_tone, pattern="^tone_")],
            ADD_RECIPIENT_SCHEDULE:      [CallbackQueryHandler(add_recipient_schedule, pattern="^(day_|days_done)")],
            ADD_RECIPIENT_SCHEDULE_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recipient_schedule_time)],
            SET_CITY:                    [MessageHandler(filters.TEXT & ~filters.COMMAND, save_city)],
            SET_SEND_MODE:               [CallbackQueryHandler(save_send_mode, pattern="^mode_")],
            PREVIEW_CONFIRM: [
                CallbackQueryHandler(confirm_send, pattern="^confirm_send_"),
                CallbackQueryHandler(send_test_to, pattern="^sendtest_"),
                CallbackQueryHandler(main_menu_handler, pattern="^back_main$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )
    app.add_handler(conv_handler)
    logger.info("HeartLine bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
