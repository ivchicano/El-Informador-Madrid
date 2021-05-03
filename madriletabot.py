import logging
import os
from threading import Lock

import telegram

from services.omw_service import OMWService
from utils.weather_conversion import weather_conversions
from telegram.utils.helpers import mention_html
from telegram.ext import Updater, CommandHandler
import sys
import traceback
import re
from datetime import timedelta


class MadriletaBot:
    def __init__(self):
        self.omw_service = OMWService()
        self.CREATOR = int(os.environ.get('CREATOR'))
        self.last_msg = ""
        self.last_msg_lock = Lock()
        # Enable logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        # Set these variable to the appropriate values
        self.TOKEN = os.environ.get('BOT_TOKEN')
        self.WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

        # Port is given by Heroku
        self.PORT = int(os.environ.get('PORT', 8080))

        # Set up the Updater
        self.updater = Updater(self.TOKEN)

        # Add to job queue the repeating task of checking OWM for changes in weather
        self.updater.job_queue.run_repeating(self.update_weather, interval=5, first=0)

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
        dp.add_error_handler(self.error)

    def time(self, update, context):
        msg = self.omw_service.get_weather()
        update.effective_message.reply_text(msg)

    def notify_subscriber(self, context):
        if weather_conversions["Clear"] != self.last_msg and weather_conversions["Clouds"] != self.last_msg:
            self.send_updates(context, self.last_msg)

    def subscribe(self, update, context):
        time_arg = " ".join(context.args)
        regex = re.compile(r'(?P<hours>\d+ ?)?(?P<minutes>\d+ ?)?(?P<seconds>\d+?)?')
        parts = regex.match(time_arg)
        if not parts:
            self.logger.error("ValueError when subscribing. Argument: " + time_arg)
            update.effective_message.reply_text("El intervalo enviado es incorrecto. Por favor comprueba que el "
                                                "formato usado es el adecuado (H M S).")
        parts = parts.groupdict()
        time_params = {}
        for (name, param) in parts.items():
            if param:
                time_params[name] = int(param)
        interval = timedelta(**time_params).total_seconds()
        # If there were jobs pertaining to this user, remove them
        jobs = context.job_queue.get_jobs_by_name(str(update.effective_chat.id))
        for job in jobs:
            job.schedule_removal()
        context.job_queue.run_repeating(self.notify_subscriber, interval, context=update.message.chat_id,
                                        name=str(update.effective_chat.id))
        update.effective_message.reply_text("Te has subscrito correctamente.")
        self.logger.info("Subscribed: " + str(update.effective_chat.id))

    def unsubscribe(self, update, context):
        jobs = context.job_queue.get_jobs_by_name(str(update.effective_chat.id))
        for job in jobs:
            job.schedule_removal()
        update.effective_message.reply_text("Te has desubscrito correctamente.")
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

    def send_updates(self, context, msg):
        self.logger.info("Sending notification: " + msg)
        # TODO: Use a message queue to avoid telegram 429 errors if there are too many messages sent
        context.bot.send_message(chat_id=int(context.job.context), text=msg)

    def notify(self, update, context):
        if update.effective_user.id != self.CREATOR:
            update.effective_message.reply_text("No eres el creador del bot.")
            self.logger.debug("User trying to use notify: %s" % update.effective_user.id)
        else:
            msg = self.omw_service.get_weather()
            self.send_updates(context, msg)

    def temperature(self, update, context):
        msg = self.omw_service.get_temperature()
        update.effective_message.reply_text(msg)

    def who_asked(self, update, context):
        msg = "¿Que quién me ha preguntado? ¿Y tú quién eres no name? Mantente madrileñófobo. Estás mad."
        update.effective_message.reply_text(msg)

    def when_in_my_region(self, update, context):
        msg = "¿Que cuándo un Informador para tu región? ¿A quién le importa tu región menor recoge patatas? Mantente " \
              "madrileñófobo. Estás mad. "
        update.effective_message.reply_text(msg)

    def que_bueno_jose(self, update, context):
        update.effective_message.reply_text("que bueno jose")

    def error(self, update, context):
        # we want to notify the user of this problem. This will always work, but not notify users if the update is an
        # callback or inline query, or a poll update. In case you want this, keep in mind that sending the message
        # could fail
        if update.effective_message:
            text = "Ha ocurrido un error inesperado. Se ha notificado al desarrollador del bot (menudo paquete)."
            update.effective_message.reply_text(text)
        # This traceback is created with accessing the traceback object from the sys.exc_info, which is returned as the
        # third value of the returned tuple. Then we use the traceback.format_tb to get the traceback as a string, which
        # for a weird reason separates the line breaks in a list, but keeps the linebreaks itself. So just joining an
        # empty string works fine.
        trace = "".join(traceback.format_tb(sys.exc_info()[2]))
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
        text = f"Hey.\n The error <code>{context.error}</code> happened{payload}. The full traceback:\n\n<code>{trace}" \
               f"</code>"
        # and send it to the dev(s)
        context.bot.send_message(self.CREATOR, text, parse_mode=telegram.ParseMode.HTML)
        # we raise the error again, so the logger module catches it. If you don't use the logger module, use it.
        raise

    def run(self):
        # Start the webhook
        self.updater.start_webhook(listen="0.0.0.0",
                                   port=self.PORT,
                                   url_path=self.TOKEN,
                                   webhook_url=self.WEBHOOK_URL)
        self.updater.idle()


if __name__ == "__main__":
    bot = MadriletaBot()
    bot.run()
