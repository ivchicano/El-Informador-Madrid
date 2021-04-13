import requests
import os
from weather_conversion import weather_conversions


class OMWService:

    def __init__(self):
        self._MAP_KEY = os.environ.get('MAP_KEY')
        self._URL = f"https://api.openweathermap.org/data/2.5/weather?q=Madrid&appid={self._MAP_KEY}&lang=es"
        self._retries = 0
        self._MAX_RETRIES = 10
        # Try connection
        requests.get(self._URL, timeout=10).raise_for_status()

    def get_weather(self):
        while self._retries < self._MAX_RETRIES:
            r = requests.get(self._URL, timeout=10)
            if r.status_code == 200:
                self._retries = 0
                weather = r.json()["weather"][0]
                main_weather = weather["main"]
                if main_weather in weather_conversions:
                    return weather_conversions[main_weather]
                else:
                    return weather["description"].capitalize() + " en Madrid"
            else:
                self._retries += 1
        raise Exception(f"Maximum number of retries reached for OpenWeatherMap requests: {self._MAX_RETRIES}")
