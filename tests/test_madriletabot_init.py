import unittest
from madriletabot import MadriletaBot
from mock import patch, MagicMock, call

clear_text = "Está clarinete Madrid"
clouds_text = "Está nublao en Madrid"
rain_text = "Está lloviendo en Madrid"
snow_text = "Está nevando en Madrid"
weather_warnings = {rain_text, snow_text}
users_list = {23242: 3600, -1234114: 7200, 43242: 1800}
weather_cycle = [clear_text, rain_text, clear_text, clouds_text, snow_text]


@patch.dict('madriletabot.os.environ', {"CREATOR": "23242", "BOT_TOKEN": "testtoken"})
@patch('madriletabot.Updater')
@patch('madriletabot.CommandHandler')
@patch('madriletabot.SubscriptionService')
@patch('madriletabot.OMWService')
def create_bot_and_mocks(omw_mock, subs_mock, cmd_handler_mock, updater_mock):
    subs_mock.return_value.get_all_users.return_value = list(users_list.keys())

    def mock_get(arg):
        returns = users_list
        return returns[arg]

    subs_mock.return_value.get.side_effect = mock_get

    context_mock = MagicMock(name='context_mock')

    madriletabot = MadriletaBot()

    return madriletabot, omw_mock, subs_mock, updater_mock, cmd_handler_mock, context_mock


class TestMadriletaBotInit(unittest.TestCase):
    def test_run(self):
        madriletabot, omw_mock, subs_mock, updater_mock, cmd_handler_mock, context_mock = \
            create_bot_and_mocks()
        updater_mock.assert_called_once_with("testtoken")
        assert madriletabot.PORT == 8080
        run_repeating_calls = [call(madriletabot.notify_subscriber, users_list[key], context=key, name=str(key))
                               for key in users_list]
        run_repeating_calls.insert(0, call(madriletabot.update_weather, 5, first=0))
        updater_mock.return_value.job_queue.run_repeating.assert_has_calls(run_repeating_calls)
        subs_mock.return_value.get_all_users.assert_called_once_with()
        subs_mock.return_value.get.assert_has_calls([call(key) for key in users_list])
        cmd_handler_calls = [call("tiempo", madriletabot.time),
                             call("subscribirse", madriletabot.subscribe),
                             call("desubscribirse", madriletabot.unsubscribe),
                             call("notificar", madriletabot.notify),
                             call("temperatura", madriletabot.temperature),
                             call("quien", madriletabot.who_asked),
                             call("cuando", madriletabot.when_in_my_region),
                             call("jose", madriletabot.que_bueno_jose)]
        cmd_handler_mock.assert_has_calls(cmd_handler_calls)
        self.assertEqual(updater_mock.return_value.dispatcher.add_handler.call_count,
                         len(cmd_handler_calls))
        updater_mock.return_value.dispatcher.add_error_handler.assert_called_once_with(madriletabot.error)


if __name__ == '__main__':
    unittest.main()
