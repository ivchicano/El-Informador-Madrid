import redis
import os


class SubscriptionService:
    def __init__(self):
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
        key = "slots:" + str(user_name) + ":" + user_id
        return self._r_conn.incrby(key, points)

    def get_ranking(self):
        keys = self._r_conn.keys("slots:*")
        result_str = ""
        result_dict = {}
        for key in keys:
            chat_name = str(key).split(":")[1]
            value = self._r_conn.get(key)
            result_dict[chat_name] = value
        for key, value in sorted(result_dict, key=result_dict.get, reverse=True):
            result_str = result_str + key + " : " + value + "\n"
        return result_str
