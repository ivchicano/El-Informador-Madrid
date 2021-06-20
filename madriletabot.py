import logging
import os
from threading import Lock

import telegram

from services.omw_service import OMWService
from services.subscription_service import SubscriptionService
from utils.slots_machine_value import slot_machine_value
from utils.weather_conversion import weather_conversions
from telegram.utils.helpers import mention_html
from telegram.ext import Updater, CommandHandler
from telegram.constants import CHATMEMBER_ADMINISTRATOR, CHATMEMBER_CREATOR
import sys
import traceback
import re
from datetime import timedelta, date, datetime
from functools import wraps


def restricted_admin(func):
    @wraps(func)
    def wrapped(self, update, context, *args, **kwargs):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        user_status = context.bot.get_chat_member(chat_id=chat_id, user_id=user_id).status
        self.logger.info("Soliciting permission. User:" + str(user_id) + " | User status: " + user_status)
        if (user_id != self.CREATOR) and (user_status != CHATMEMBER_CREATOR) and (
                user_status != CHATMEMBER_ADMINISTRATOR):
            update.message.reply_text("No tienes permisos para ejecutar este comando")
            return
        return func(self, update, context, *args, **kwargs)

    return wrapped


def check_cd(func):
    @wraps(func)
    def wrapped(self, update, context, *args, **kwargs):
        chat_id = update.effective_chat.id
        cd = self.subscription_service.get_cooldown(chat_id)
        self.logger.info("Checking cd: " + str(cd) + " of chat: " + str(chat_id))
        if cd is not None:
            user_id = update.effective_user.id
            self.logger.info("User: " + str(user_id))
            last_time = self.cds_user.get(user_id)
            now = datetime.now()
            self.cds_user.update({user_id: now})
            if last_time is not None:
                time_passed = now - last_time
                delta_cd = timedelta(seconds=int(cd))
                self.logger.info(
                    "User last time: " + last_time.strftime("%m/%d/%Y, %H:%M:%S") + ". Current time: " + now.strftime(
                        "%m/%d/%Y, %H:%M:%S") + ". Time passed: " + str(time_passed) + ". delta_cd: " + str(delta_cd))
                if time_passed < delta_cd:
                    update.message.reply_text(
                        "Relaja la raja socio. Podrás mandar un comando en " + str((last_time + delta_cd) - now)
                        + " s")
                    return
                else:
                    self.logger.info("Not on cooldown, running...")
                    return func(self, update, context, *args, **kwargs)
            else:
                self.logger.info("No last time found, setting...")
                return func(self, update, context, *args, **kwargs)
        else:
            self.logger.info("No cd found")
            return func(self, update, context, *args, **kwargs)

    return wrapped


class MadriletaBot:
    def __init__(self):
        self.omw_service = OMWService()
        self.subscription_service = SubscriptionService()
        self.CREATOR = int(os.environ.get('CREATOR'))
        self.last_msg = ""
        self.last_msg_lock = Lock()
        # Enable logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)
        logging.getLogger('apscheduler').setLevel(logging.WARNING)
        self.logger = logging.getLogger(__name__)
        # Set these variable to the appropriate values
        self.TOKEN = os.environ.get('BOT_TOKEN')

        # Port is given by Heroku
        self.PORT = int(os.environ.get('PORT', 8080))

        # Set up the Updater
        self.updater = Updater(self.TOKEN)

        self.update_weather()
        # Add to job queue the repeating task of checking OWM for changes in weather
        self.updater.job_queue.run_repeating(self.update_weather_job, 5, first=0)

        self.cds_user = {}

        self.cooldowns = {}

        for key in self.subscription_service.get_all_users():
            self.logger.info(str(key))
            chat_id = int(str(key)[4:])
            self.cooldowns.update({chat_id: date(1970, 1, 1)})

        dp = self.updater.dispatcher
        # Add handlers
        dp.add_handler(CommandHandler('tiempo', self.time))
        dp.add_handler(CommandHandler('subscribirse', self.subscribe))
        dp.add_handler(CommandHandler('desubscribirse', self.unsubscribe))
        dp.add_handler(CommandHandler('notificar', self.notify))
        dp.add_handler(CommandHandler('temperatura', self.temperature))
        dp.add_handler(CommandHandler('quien', self.who_asked))
        dp.add_handler(CommandHandler('cuando', self.when_in_my_region))
        dp.add_handler(CommandHandler('jose', self.que_bueno_jose))
        dp.add_handler(CommandHandler('slots', self.slots))
        dp.add_handler(CommandHandler('ranking', self.send_ranking))
        dp.add_handler(CommandHandler('setcd', self.set_cd))
        dp.add_handler(CommandHandler('removecd', self.remove_cd))
        dp.add_error_handler(self.error)

    @restricted_admin
    @check_cd
    def set_cd(self, update, context):
        cd_arg = " ".join(context.args)
        regex = re.compile(r'(?P<seconds>\d+)')
        parts = regex.match(cd_arg)
        if not parts:
            self.logger.error("ValueError when setting cd. Argument: " + cd_arg)
            update.effective_message.reply_text("El enfriamiento enviado es incorrecto. Por favor comprueba que el "
                                                "formato usado es el adecuado (s).")
        else:
            self.subscription_service.set_cooldown(update.effective_chat.id, parts["seconds"])
            update.message.reply_text("Enfriamiento configurado correctamente.")

    @check_cd
    def remove_cd(self, update, context):
        self.subscription_service.remove_cooldown(update.effective_chat.id)
        update.effective_message.reply_text("El enfriamiento se ha eliminado correctamente.")

    @check_cd
    def time(self, update, context):
        msg = self.omw_service.get_weather()
        update.effective_message.reply_text(msg)

    @check_cd
    def subscribe(self, update, context):
        time_arg = " ".join(context.args)
        regex = re.compile(r'(?P<hours>\d+) (?P<minutes>\d+) (?P<seconds>\d+)')
        parts = regex.match(time_arg)
        if not parts:
            self.logger.error("ValueError when subscribing. Argument: " + time_arg)
            update.effective_message.reply_text("El enfriamiento enviado es incorrecto. Por favor comprueba que el "
                                                "formato usado es el adecuado (H M S).")
        else:
            parts = parts.groupdict()
            time_params = {}
            for (name, param) in parts.items():
                if param:
                    time_params[name] = int(param)
            cooldown = timedelta(**time_params).total_seconds()
            if cooldown <= 0:
                self.logger.error("Cooldown lower or 0. Argument: " + time_arg)
                update.effective_message.reply_text("Por favor introduce un valor mayor que 0.")
            else:
                self.cooldowns.update({int(update.effective_chat.id): date(1970, 1, 1)})
                # Register in redis
                self.subscription_service.subscribe(update.effective_chat.id, cooldown)
                update.effective_message.reply_text("Te has subscrito correctamente.")
                self.logger.info("Subscribed: " + str(update.effective_chat.id) + ", " + str(cooldown))

    @check_cd
    def unsubscribe(self, update, context):
        jobs = context.job_queue.get_jobs_by_name(str(update.effective_chat.id))
        for job in jobs:
            job.schedule_removal()
        update.effective_message.reply_text("Te has desubscrito correctamente.")
        self.subscription_service.unsubscribe(update.effective_chat.id)
        self.logger.info("Unsubscribed: " + str(update.effective_chat.id))

    def update_weather(self):
        msg = self.omw_service.update_weather()
        acquired = self.last_msg_lock.acquire(timeout=5)
        try:
            if not acquired:
                raise Exception("Timeout when acquiring last msg lock")
            if self.last_msg != msg:
                self.logger.info("Saving new message. Previous " + self.last_msg + ". New: " + msg)
                self.last_msg = msg
        finally:
            self.last_msg_lock.release()

    def update_weather_job(self, context):
        try:
            self.update_weather()
            if weather_conversions["Clear"] != self.last_msg and weather_conversions["Clouds"] != self.last_msg:
                self.send_updates(context, self.last_msg)
        except:
            self.error_job()

    def send_updates(self, context, msg):
        self.logger.info("Sending notification: " + msg)
        # TODO: Use a message queue to avoid telegram 429 errors if there are too many messages sent
        users = self.subscription_service.get_all_users()
        self.logger.info("Subbed: " + str(users))
        for key in users:
            chat_id = int(str(key)[4:])
            cooldown = timedelta(seconds=float(self.subscription_service.get(key)))
            last_sent = self.cooldowns.get(chat_id, date(1970, 1, 1))
            now = datetime.today()
            self.logger.info(
                "For user: " + str(chat_id) + ". Cooldown: " + str(cooldown) + ". Last sent: " + str(last_sent))
            if (now - last_sent) > cooldown:
                self.logger.info("Sending to: " + str(chat_id))
                context.bot.send_message(chat_id=chat_id, text=msg)
                self.cooldowns.update({chat_id: now})

    @check_cd
    def notify(self, update, context):
        if update.effective_user.id != self.CREATOR:
            update.effective_message.reply_text("No eres el creador del bot.")
            self.logger.debug("User trying to use notify: %s" % update.effective_user.id)
        else:
            msg = self.omw_service.get_weather()
            for job in context.job_queue.jobs():
                context.bot.send_message(chat_id=int(job.context), text=msg)

    @check_cd
    def temperature(self, update, context):
        msg = self.omw_service.get_temperature()
        update.effective_message.reply_text(msg)

    @check_cd
    def who_asked(self, update, context):
        msg = "¿Que quién me ha preguntado? ¿Y tú quién eres no name? Mantente madrileñófobo. Estás mad."
        update.effective_message.reply_text(msg)

    @check_cd
    def when_in_my_region(self, update, context):
        msg = "¿Que cuándo un Informador para tu región? ¿A quién le importa tu región menor recoge patatas? Mantente " \
              "madrileñófobo. Estás mad. "
        update.effective_message.reply_text(msg)

    @check_cd
    def que_bueno_jose(self, update, context):
        update.effective_message.reply_text("que bueno jose")

    @check_cd
    def send_ranking(self, update, context):
        context.bot.send_message(update.effective_chat.id, text=self.subscription_service.get_ranking())

    def update_ranking(self, user_name, user_id, points):
        self.subscription_service.update_ranking(user_name, user_id, points)

    @check_cd
    def slots(self, update, context):
        result = context.bot.send_dice(update.effective_chat.id, emoji="🎰",
                                       reply_to_message_id=update.effective_message.message_id)
        if result.dice.value in slot_machine_value:
            converted_results = slot_machine_value[result.dice.value]
            self.update_ranking(update.effective_user.first_name, update.effective_user.id, converted_results)
        else:
            self.update_ranking(update.effective_user.first_name, update.effective_user.id, -10)

    def error(self, update, context):
        exc_info = sys.exc_info()
        self.logger.error(exc_info[0])
        self.logger.error(exc_info[1])
        self.logger.error(traceback.format_tb(sys.exc_info()[2]))
        self.logger.error(context)
        self.logger.error(update)
        if update is None:
            self.error_job()
        else:
            # we want to notify the user of this problem. This will always work, but not notify users if the update
            # is an callback or inline query, or a poll update. In case you want this, keep in mind that sending the
            # message could fail
            if update.effective_message:
                text = "Ha ocurrido un error inesperado. Se ha notificado al desarrollador del bot (menudo paquete)."
                update.effective_message.reply_text(text)
            # This traceback is created with accessing the traceback object from the sys.exc_info, which is returned
            # as the third value of the returned tuple. Then we use the traceback.format_tb to get the traceback as a
            # string, which for a weird reason separates the line breaks in a list, but keeps the linebreaks itself.
            # So just joining an empty string works fine.
            trace = "".join(traceback.format_tb(exc_info[2]))
            # lets try to get as much information from the telegram update as possible
            payload = ""
            # normally, we always have an user. If not, its either a channel or a poll update.
            if update.effective_user:
                payload += f' with the user {mention_html(update.effective_user.id, update.effective_user.first_name)}'
            # there are more situations when you don't get a chat
            if update.effective_chat:
                payload += f' within the chat <i>{update.effective_chat.title}</i>'
                if update.effective_chat.username:
                    payload += f' (@{update.effective_chat.username})'
            # but only one where you have an empty payload by now: A poll (buuuh)
            if update.poll:
                payload += f' with the poll id {update.poll.id}.'
            # lets put this in a "well" formatted text
            text = f"Hey.\n The error <code>{context.error}</code> happened{payload}." \
                   f" The full traceback:\n\n<code>{trace}" \
                   f"</code>"
            # and send it to the dev(s)
            context.bot.send_message(self.CREATOR, text, parse_mode=telegram.ParseMode.HTML)
            # we raise the error again, so the logger module catches it. If you don't use the logger module, use it.
            raise

    def error_job(self):
        exc_info = sys.exc_info()
        if (exc_info[0] is not None) or (exc_info[1] is not None) or (exc_info[2] is not None):
            text = f"Type: <code>{exc_info[0]}</code>\n\n" \
                   f"Value: <code>{exc_info[1]}</code>\n\n" \
                   f"Traceback: <code>{exc_info[2]}</code>"
            self.updater.bot.send_message(self.CREATOR, text, parse_mode=telegram.ParseMode.HTML)

    def run(self):
        # Start the webhook
        if os.environ.get('HEROKU') == 'True':
            WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
            self.updater.start_webhook(listen="0.0.0.0",
                                       port=self.PORT,
                                       url_path=self.TOKEN,
                                       webhook_url=WEBHOOK_URL)
        else:
            self.updater.start_polling()
        self.updater.idle()


if __name__ == "__main__":
    bot = MadriletaBot()
    bot.run()
