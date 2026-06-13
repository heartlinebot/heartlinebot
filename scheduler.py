import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

DAY_MAP = {
    "mon": "mon", "tue": "tue", "wed": "wed",
    "thu": "thu", "fri": "fri", "sat": "sat", "sun": "sun",
    "everyday": "mon,tue,wed,thu,fri,sat,sun"
}


class MessageScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        logger.info("Scheduler started")

    def schedule_recipient(self, recipient_id, user_id, days, time_str, context):
        job_id = f"rec_{recipient_id}"

        # Видалити старий job якщо є
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

        try:
            hour, minute = map(int, time_str.split(":"))
        except ValueError:
            hour, minute = 9, 0

        # Визначити дні
        if 'everyday' in days:
            day_of_week = "mon,tue,wed,thu,fri,sat,sun"
        else:
            day_of_week = ",".join([DAY_MAP.get(d, d) for d in days])

        self.scheduler.add_job(
            func=self._send_scheduled,
            trigger=CronTrigger(
                day_of_week=day_of_week,
                hour=hour,
                minute=minute
            ),
            id=job_id,
            kwargs={
                "recipient_id": recipient_id,
                "user_id": user_id,
                "bot": context.bot if context else None,
            },
            replace_existing=True
        )
        logger.info(f"Scheduled job {job_id}: {day_of_week} at {time_str}")

    async def _send_scheduled(self, recipient_id, user_id, bot):
        if not bot:
            return
        try:
            from database import Database
            from ai_generator import generate_message
            from weather import get_weather

            db = Database()
            recipient = db.get_recipient(recipient_id)
            user = db.get_user(user_id)

            if not recipient or not user:
                return

            city = user.get('city', '')
            weather_info = await get_weather(city) if city else ""
            send_mode = user.get('send_mode', 'auto')

            message_text = await generate_message(
                recipient_name=recipient['name'],
                relation=recipient['relation'],
                tone=recipient['tone'],
                city=city,
                weather=weather_info
            )

            if send_mode == 'auto':
                contact = recipient['contact']
                if contact.startswith('@'):
                    await bot.send_message(chat_id=contact, text=message_text)
                    db.log_message(user_id, recipient_id, message_text, "sent")
                    logger.info(f"Auto-sent to {contact}")

            elif send_mode == 'preview':
                await bot.send_message(
                    chat_id=user_id,
                    text=f"👁 *Готово до надсилання {recipient['name']}:*\n\n"
                         f"{message_text}\n\n"
                         f"Підтвердити надсилання?",
                    parse_mode="Markdown"
                )

            elif send_mode == 'manual':
                await bot.send_message(
                    chat_id=user_id,
                    text=f"✏️ *Чернетка для {recipient['name']}:*\n\n"
                         f"{message_text}\n\n"
                         f"Відредагуй і надішли вручну.",
                    parse_mode="Markdown"
                )

        except Exception as e:
            logger.error(f"Scheduled send error for recipient {recipient_id}: {e}")

    def restore_schedules(self, db, context):
        """Відновити всі розклади після перезапуску бота"""
        recipients = db.get_all_active_recipients()
        for r in recipients:
            days = r['schedule_days'].replace(" ", "").split(",")
            self.schedule_recipient(
                recipient_id=r['id'],
                user_id=r['user_id'],
                days=days,
                time_str=r['schedule_time'],
                context=context
            )
        logger.info(f"Restored {len(recipients)} scheduled jobs")
