import unittest
from madriletabot import MadriletaBot
from mock import patch, MagicMock, call

clear_text = "Está clarinete Madrid"
clouds_text = "Está nublao en Madrid"
rain_text = "Está lloviendo en Madrid"
snow_text = "Está nevando en Madrid"
weather_warnings = {rain_text, snow_text}
users_list = [23242, -1234114, 43242]


@patch('madriletabot.os')
@patch('madriletabot.OMWService')
def test_update_weather(new_msgs, omw_mock, os_mock):
    omw_instance_mock = MagicMock(name="omw_instance_mock")
    omw_instance_mock.update_weather.side_effect = new_msgs
    omw_mock.return_value = omw_instance_mock

    def os_environ_get_mock_side_effect(arg):
        if arg == 'CREATOR':
            return 23242
        else:
            return None

    os_mock.environ.get.side_effect = os_environ_get_mock_side_effect
    context = MagicMock(name='context')
    send_message_mock = context.bot.send_message

    madriletabot = MadriletaBot()
    for msg in new_msgs:
        madriletabot.update_weather()

    return madriletabot, omw_instance_mock, send_message_mock


class TestMadriletaBot(unittest.TestCase):

    def update_weather_assertions(self, madriletabot, msgs, omw_mock,
                                  send_message_mock):

        # Last message should be the last message received
        self.assertEqual(msgs[len(msgs) - 1], madriletabot.last_msg)
        # Update weather called for each tick
        self.assertEqual(omw_mock.update_weather.call_count, len(msgs))
        # For each weather warning a message should be sent to each user
        calls = []
        previous_msg = ""
        send_updates_calls = 0
        for msg in msgs:
            # If a message has already been sent before it shouldn't be sent again
            if previous_msg != msg:
                previous_msg = msg
                if msg in weather_warnings:
                    send_updates_calls += 1
                    for user in users_list:
                        calls.append(call(chat_id=user, text=msg))
        # Message should be sent for each weather warning
        self.assertEqual(send_message_mock.call_count, len(users_list) * send_updates_calls)
        send_message_mock.assert_has_calls(calls)

    def test_update_weather_1(self):
        # Clear > Clouds
        msgs = [clear_text, clouds_text]

        madriletabot, omw_mock, send_message_mock = \
            test_update_weather([clear_text, clouds_text])

        self.update_weather_assertions(madriletabot, msgs, omw_mock, send_message_mock)

    def test_update_weather_2(self):
        # Clear > Rain > Clear
        msgs = [clear_text, rain_text, clear_text]

        madriletabot, omw_mock, send_message_mock = \
            test_update_weather(msgs)

        self.update_weather_assertions(madriletabot, msgs, omw_mock, send_message_mock)

    def test_update_weather_3(self):
        # Clear > Rain > Snow > Cloud > Clear > Rain
        msgs = [clear_text, rain_text, snow_text, clouds_text, clear_text, rain_text]

        madriletabot, omw_mock, send_message_mock = \
            test_update_weather(msgs)

        self.update_weather_assertions(madriletabot, msgs, omw_mock, send_message_mock)

    def test_update_weather_4(self):
        # Clear > Drizzle > Rain > Drizzle > Cloud > Clear > Rain > Drizzle
        msgs = [clear_text, rain_text, rain_text, rain_text, clouds_text, clear_text, rain_text, rain_text]

        madriletabot, omw_mock, send_message_mock = \
            test_update_weather(msgs)

        self.update_weather_assertions(madriletabot, msgs, omw_mock, send_message_mock)


if __name__ == '__main__':
    unittest.main()
