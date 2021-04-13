weather_conversions = {
    "Thunderstorm": "Hay tormenta en Madrid",
    "Drizzle": "Está lloviendo en Madrid",
    "Rain": "Está lloviendo en Madrid",
    "Snow": "Está nevando en Madrid",
    "Clouds": "Está nublao en Madrid",
    "Clear": "Se está DPM en Madrid",
}


def temperature_conversions(temp):
    if temp < 5:
        temp_result = "Hace un frío que pela"
    elif temp < 10:
        temp_result = "Ponte una rebequita que refresca"
    elif temp < 20:
        temp_result = "Hace fresquibiri"
    elif temp < 25:
        temp_result = "Se está de lujo"
    elif temp < 30:
        temp_result = "Hase calorsito"
    elif temp < 35:
        temp_result = "Te va a brillar la calva como salgas"
    else:
        temp_result = "La temperatura de cocción del guiri es idónea"
    return f"{temp_result} en Madrid ({temp} ºC)"
