import requests
import os
from utils.weather_conversion import weather_conversions, temperature_conversions


class OMWService:

    def __init__(self):
        self._MAP_KEY = os.environ.get('MAP_KEY')
        self._URL = f"https://api.openweathermap.org/data/2.5/weather?q=Madrid&appid={self._MAP_KEY}&lang=es&units=metric"
        self._retries = 0
        self._MAX_RETRIES = 10
        # Try connection
        self._make_query()

    def _make_query(self):
        while self._retries < self._MAX_RETRIES:
            r = requests.get(self._URL, timeout=4)
            if r.status_code == 200:
                self._retries = 0
                r.raise_for_status()
                self.last_weather = r.json()
                return r
            else:
                self._retries += 1
        raise Exception(f"Maximum number of retries reached for OpenWeatherMap requests: {self._MAX_RETRIES}")

    def get_weather(self):
        weather = self.last_weather["weather"][0]
        main_weather = weather["main"]
        if main_weather in weather_conversions:
            return weather_conversions[main_weather]
        else:
            return weather["description"].capitalize() + " en Madrid"

    def update_weather(self):
        self._make_query()
        return self.get_weather()

    def get_temperature(self):
        temperature = self.last_weather["main"]["temp"]
        return temperature_conversions(temperature)
