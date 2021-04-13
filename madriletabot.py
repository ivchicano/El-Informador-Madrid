import logging
import os

import telegram

from subscription_service import SubscriptionService
from omw_service import OMWService
from weather_conversion import weather_conversions
from telegram.utils.helpers import mention_html
from telegram.ext import Updater, CommandHandler
from telegram.ext import messagequeue as mq
import sys
import traceback


# TODO: command "quien"
# TODO: command "temperatura"


class MQBot(telegram.bot.Bot):
    """A subclass of Bot which delegates send method handling to MQ"""

    def __init__(self, *args, is_queued_def=True, mqueue=None, **kwargs):
        super(MQBot, self).__init__(*args, **kwargs)
        # below 2 attributes should be provided for decorator usage
        self._is_messages_queued_default = is_queued_def
        self._msg_queue = mqueue or mq.MessageQueue()

    def __del__(self):
        try:
            self._msg_queue.stop()
        except:
            pass

    @mq.queuedmessage
    def send_message(self, *args, **kwargs):
        """Wrapped method would accept new `queued` and `isgroup`
        OPTIONAL arguments"""
        return super(MQBot, self).send_message(*args, **kwargs)


subscription_service = SubscriptionService()
omw_service = OMWService()
CREATOR = int(os.environ.get('CREATOR'))


def time(update, context):
    msg = omw_service.get_weather()
    update.effective_message.reply_text(msg)


def subscribe(update, context):
    subscription_service.subscribe(update.effective_chat.id)
    update.effective_message.reply_text("Te has subscrito correctamente.")


def unsubscribe(update, context):
    subscription_service.unsubscribe(update.effective_chat.id)
    update.effective_message.reply_text("Te has desubscrito correctamente.")


last_msg = ""


def update_weather(context):
    msg = omw_service.get_weather()
    global last_msg
    if last_msg != msg:
        last_msg = msg
        if weather_conversions["Clear"] != last_msg and weather_conversions["Clouds"] != last_msg:
            send_updates(context, last_msg)


def send_updates(context, msg):
    chat_ids = subscription_service.get_all_users()
    # TODO: Use a message queue to avoid telegram 429 errors if there are too many messages sent
    for chat_id in chat_ids:
        context.bot.send_message(chat_id=int(chat_id), text=msg)


def notify(update, context):
    if update.effective_user.id != CREATOR:
        update.effective_message.reply_text("No eres el creador del bot.")
        logger.debug("User trying to use notify: %s" % update.effective_user.id)
    else:
        msg = omw_service.get_weather()
        send_updates(context, msg)


def error(update, context):
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
    context.bot.send_message(CREATOR, text, parse_mode=telegram.ParseMode.HTML)
    # we raise the error again, so the logger module catches it. If you don't use the logger module, use it.
    raise


if __name__ == "__main__":
    # Set these variable to the appropriate values
    TOKEN = os.environ.get('BOT_TOKEN')
    WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

    # Port is given by Heroku
    PORT = int(os.environ.get('PORT', 8080))

    # Enable logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    # Set up the Updater
    updater = Updater(TOKEN)

    # Add to job queue the repeating task of checking OWM for changes in weather

    job_q = updater.job_queue

    job_q.run_repeating(update_weather, interval=6, first=0)

    dp = updater.dispatcher
    # Add handlers
    dp.add_handler(CommandHandler('tiempo', time))
    dp.add_handler(CommandHandler('subscribirse', subscribe))
    dp.add_handler(CommandHandler('desubscribirse', unsubscribe))
    dp.add_handler(CommandHandler('notificar', notify))
    dp.add_error_handler(error)

    # Start the webhook
    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN,
                          webhook_url=WEBHOOK_URL)
    updater.idle()
