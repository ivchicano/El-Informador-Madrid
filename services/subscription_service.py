import redis
import os


class SubscriptionService:
    def __init__(self):
        self._r_conn = redis.from_url(os.environ.get("REDIS_URL"))
        # Check connection
        self._r_conn.ping()

    def subscribe(self, chat_id, value):
        return self._r_conn.set(chat_id, value)

    def unsubscribe(self, chat_id):
        return self._r_conn.delete(chat_id)

    def get_all_users(self):
        return self._r_conn.keys("*")

    def get(self, chat_id):
        return self._r_conn.get(chat_id)