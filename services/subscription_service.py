import redis
import os
import logging


class SubscriptionService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._r_conn = redis.from_url(os.environ.get("REDIS_URL"), charset="utf-8", decode_responses=True)
        # Check connection
        self._r_conn.ping()

    def subscribe(self, chat_id, value):
        return self._r_conn.set(chat_id, value)

    def unsubscribe(self, chat_id):
        return self._r_conn.delete(chat_id)

    def get_all_users(self):
        return self._r_conn.keys("sub:*")

    def get(self, chat_id):
        return self._r_conn.get(chat_id)

    def update_ranking(self, user_name, user_id, points):
        keys = self._r_conn.keys("slots:*:" + user_id)
        key = "slots:" + str(user_name) + ":" + str(user_id)
        if (len(keys) > 0) and (keys[0] != key):  # user name changed and has to be updated
            value = self._r_conn.get(keys[0])
            self._r_conn.delete(keys[0])
            return self._r_conn.set(key, value + points)
        return self._r_conn.incrby(key, points)

    def get_ranking(self):
        keys = self._r_conn.keys("slots:*")
        result_str = ""
        result_dict = {}
        for key in keys:
            chat_name = str(key).split(":")[1]
            value = self._r_conn.get(key)
            result_dict[chat_name] = int(value)
        self.logger.info(result_dict)
        for item in sorted(result_dict.items(), key=lambda x: x[1], reverse=True):
            result_str = result_str + item[0] + " : " + str(item[1]) + "\n"
        return result_str

    def get_points(self, user_id):
        keys = self._r_conn.keys("slots:*:" + str(user_id))
        if len(keys) <= 0:
            return 0
        return int(self._r_conn.get(keys[0]))

    def set_cooldown(self, chat_id, seconds):
        return self._r_conn.set("cooldown:" + str(chat_id), seconds)

    def get_cooldown(self, chat_id):
        return self._r_conn.get("cooldown:" + str(chat_id))

    def remove_cooldown(self, chat_id):
        self._r_conn.delete("cooldown:" + str(chat_id))
