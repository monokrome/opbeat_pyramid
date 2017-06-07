import collections
import functools
import mock
import os
import unittest

from pyramid import httpexceptions
from pyramid import testing

from opbeat_pyramid import subscribers


MOCK_APP_ID = 'mock app id'
MOCK_SECRET_TOKEN = 'mock secret token'

SETTING_NAME = 'mock_setting'
EXPECTED_VALUE = 'Expected Value'
UNEXPECTED_VALUE = 'Unexpected Value'

ENV_SETTING_NAME = 'mock_env_setting'
EXPECTED_ENV_VALUE = 'Expected Env Value'
UNEXPECTED_ENV_VALUE = 'Unexpected Env Value'

DEFAULT_VALUE = 'Default Value'

MOCK_QUERY_STRING = 'mock&query=string'

MOCK_USER_AGENT = (
    'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0 like Mac OS X) '
    'AppleWebKit/534.46 (KHTML, like Gecko) '
    'Version/5.1 Mobile/9A334 Safari/7534.48.3'
)

MockRequestEvent = collections.namedtuple('RequestEvent', 'request')


class OpbeatSubscribersTestCase(unittest.TestCase):
    def setUp(self):
        setting_key = 'opbeat.' + SETTING_NAME

        self.config = testing.setUp()
        self.request = testing.DummyRequest(self.config)

        self.request.client_addr = '0.0.0.0'
        self.request.exc_info = None
        self.request.host = 'example.com:443'
        self.request.scheme = 'https'
        self.request.user_agent = MOCK_USER_AGENT

        self.request.matched_route = mock.MagicMock()
        self.request.matched_route.name = 'example_view'

        self.settings = self.request.registry.settings = {
            setting_key: EXPECTED_VALUE,
            'mock_setting': UNEXPECTED_VALUE,
            'opbeat.enabled': 'true',
            'opbeat.module_name': 'mock',
            'opbeat.app_id': 'mock app id',
            'opbeat.secret_token': MOCK_SECRET_TOKEN,
            'opbeat.organization_id': MOCK_SECRET_TOKEN,
        }

        os.environ['OPBEAT_MOCK_ENV_SETTING'] = EXPECTED_ENV_VALUE
        os.environ['MOCK_ENV_SETTING'] = UNEXPECTED_ENV_VALUE

    def tearDown(self):
        del os.environ['OPBEAT_MOCK_ENV_SETTING']
        del os.environ['MOCK_ENV_SETTING']

    def test_get_opbeat_setting_gets_value_from_request_settings(self):
        value = subscribers.get_opbeat_setting(self.request, SETTING_NAME)
        self.assertIs(value, EXPECTED_VALUE)

    def test_get_opbeat_setting_gets_value_from_env_settings(self):
        value = subscribers.get_opbeat_setting(self.request, ENV_SETTING_NAME)
        self.assertEqual(value, EXPECTED_ENV_VALUE)

    def test_get_opbeat_setting_prefers_environment_over_settings(self):
        local_name = 'opbeat_some_setting'
        local_name_upper = local_name.upper()

        os.environ[local_name_upper] = EXPECTED_ENV_VALUE
        value = subscribers.get_opbeat_setting(self.request, 'some_setting')
        del os.environ[local_name_upper]

        self.assertEqual(value, EXPECTED_ENV_VALUE)

    def test_get_opbeat_setting_returns_default_when_not_set(self):
        self.assertIs(DEFAULT_VALUE, subscribers.get_opbeat_setting(
            self.request,
            'unknown_setting',
            default=DEFAULT_VALUE,
        ))

    def test_get_opbeat_setting_raises_ValueError_without_a_default(self):
        break_shit = functools.partial(
            subscribers.get_opbeat_setting,
            self.request,
            'unknown_setting',
        )

        self.assertRaises(ValueError, break_shit)

    @mock.patch('opbeat.Client')
    def test_opbeat_client_factory_returns_an_opbeat_client(self, Client):
        MOCK_RETURN_VALUE = {}
        Client.return_value = MOCK_RETURN_VALUE

        result = subscribers.opbeat_client_factory(self.request)
        Client.assert_called_once()

        self.assertIs(result, MOCK_RETURN_VALUE)

    @mock.patch('opbeat.Client')
    def test_opbeat_client_factory_caches_by_app_id(self, Client):
        subscribers.opbeat_client_factory(self.request)
        subscribers.opbeat_client_factory(self.request)
        Client.assert_called_once()

    @mock.patch('opbeat.Client')
    def test_opbeat_client_factory_wont_cache_separate_apps(self, Client):
        subscribers.opbeat_client_factory(self.request)

        self.settings['opbeat.app_id'] = 'Another App ID'
        subscribers.opbeat_client_factory(self.request)

        self.assertEqual(Client.call_count, 2)

    def test_setting_is_enabled_returns_true_for_truthy_values(self):
        is_enabled = functools.partial(
            subscribers.setting_is_enabled,
            self.request,
            'truthy_value',
        )

        self.settings['opbeat.truthy_value'] = True
        self.assertTrue(is_enabled())

        self.settings['opbeat.truthy_value'] = 'true'
        self.assertTrue(is_enabled())

        self.settings['opbeat.truthy_value'] = 'on'
        self.assertTrue(is_enabled())

        self.settings['opbeat.truthy_value'] = 'yes'
        self.assertTrue(is_enabled())

    def test_setting_is_enabled_returns_false_for_falsy_values(self):
        is_enabled = functools.partial(
            subscribers.setting_is_enabled,
            self.request,
            'truthy_value',
        )

        self.settings['opbeat.truthy_value'] = False
        self.assertFalse(is_enabled())

        self.settings['opbeat.truthy_value'] = 'false'
        self.assertFalse(is_enabled())

        self.settings['opbeat.truthy_value'] = 'off'
        self.assertFalse(is_enabled())

        self.settings['opbeat.truthy_value'] = 'no'
        self.assertFalse(is_enabled())

    def test_get_request_module_name_returns_module_name_from_settings(self):
        module_name = subscribers.get_request_module_name(self.request)
        self.assertEqual(module_name, 'mock')

    def test_get_request_module_name_returns_default_if_setting_missing(self):
        del self.settings['opbeat.module_name']

        module_name = subscribers.get_request_module_name(self.request)
        self.assertEqual(module_name, 'UNKNOWN_MODULE')

    def test_get_safe_settings_returns_settings_without_unsafe_keywords(self):
        MOCK_KEYS = [
            'unsafe_token', 'SECRET_ID', 'MockPassword',
            'passphrase', 'private_item', 'local_key',
        ]

        del self.settings['opbeat.secret_token']

        for key in MOCK_KEYS:
            absolute_key = 'opbeat.' + key
            self.settings[absolute_key] = 'mock unsafe token'

        results = subscribers.get_safe_settings(self.request)

        num_results = len(results.keys())
        num_settings = len(self.settings)
        num_bad_keys = len(MOCK_KEYS)

        for key in MOCK_KEYS:
            self.assertNotIn('opbeat.' + key, results)

        self.assertEqual(num_results, num_settings - num_bad_keys)

    def test_should_ignore_HttpException_returns_false_by_default(self):
        mock_exc_info = [None, httpexceptions.HTTPNotFound()]

        self.assertFalse(subscribers.should_ignore_exception(
            self.request,
            mock_exc_info,
        ))

    def test_should_ignore_HttpException_returns_true_when_enabled(self):
        settings = self.settings
        settings['opbeat.ignore_http_exceptions'] = 'true'
        mock_exc_info = [None, httpexceptions.HTTPNotFound()]

        self.assertTrue(subscribers.should_ignore_exception(
            self.request,
            mock_exc_info,
        ))

    def test_should_not_ignore_exceptions_unless_they_are_HttpExceptions(self):
        self.settings['opbeat.ignore_http_exceptions'] = 'true'
        mock_exc_info = [None, ValueError()]

        self.assertFalse(subscribers.should_ignore_exception(
            self.request,
            mock_exc_info,
        ))

    def test_should_ignore_HttpException_returns_false_when_disabled(self):
        self.settings['opbeat.ignore_http_exceptions'] = 'false'
        mock_exc_info = [None, httpexceptions.HTTPNotFound()]

        self.assertFalse(subscribers.should_ignore_exception(
            self.request,
            mock_exc_info,
        ))

    @mock.patch('opbeat.Client')
    def test_capture_exception_ignores_errors_from_opbeat_client(self, Client):
        # NOTE: This uses a catchall which seems bad, but we do it right now.

        client = mock.MagicMock()
        client.capture_exception.side_effect = ValueError()
        Client.return_value = client

        mock_exc_info = [None, ValueError()]

        self.assertRaises(ValueError, client.capture_exception)
        subscribers.capture_exception(self.request, mock_exc_info, extra={})
        self.assertEqual(2, client.capture_exception.call_count)

    @mock.patch('opbeat.Client')
    def test_handle_exception_sends_an_exception_to_opbeat(self, Client):
        client = mock.MagicMock()
        Client.return_value = client

        self.request.query_string = MOCK_QUERY_STRING
        mock_exc_info = [None, ValueError()]

        subscribers.handle_exception(self.request, mock_exc_info)

        expected_data = {
            'http': {
                'url': 'https://example.com:443/',
                'method': 'GET',
                'query_string': MOCK_QUERY_STRING,
            }
        }

        mock_extra_metadata = {
            'client_ip_address': self.request.client_addr,
            'logging_successful': 'true',
            'url': self.request.url,
            'user_agent': self.request.user_agent,
        }

        mock_extra_metadata.update(subscribers.get_safe_settings(self.request))

        client.capture_exception.assert_called_once_with(
            mock_exc_info,
            data=expected_data,
            extra=mock_extra_metadata,
        )

    @mock.patch('opbeat.Client')
    @mock.patch('opbeat_pyramid.subscribers.should_ignore_exception')
    def test_handle_exception_ignores_ignored_exceptions(self, mock, Client):
        mock.return_value = True
        mock_exc_info = [None, httpexceptions.HTTPNotFound()]

        client = mock.MagicMock()
        Client.return_value = client

        subscribers.handle_exception(self.request, mock_exc_info)
        mock.assert_called_once_with(self.request, mock_exc_info)
        client.capture_exception.assert_not_called()

    def test_get_exception_for_request_returns_exc_info_if_not_None(self):
        self.request.exc_info = ''
        exc_info = subscribers.get_exception_for_request(self.request)
        self.assertIs(exc_info, self.request.exc_info)

    @mock.patch('sys.exc_info')
    def test_get_exception_for_request_uses_sys_as_fallback(self, _exc_info):
        e = ValueError()
        mock_exc_info = (type(e), e)

        self.request.exc_info = None
        _exc_info.return_value = mock_exc_info
        exc_info = subscribers.get_exception_for_request(self.request)
        self.assertEquals(exc_info, mock_exc_info)
        _exc_info.assert_called_once()

    @mock.patch('sys.exc_info')
    def test_get_exception_for_request_no_exception(self, _exc_info):
        self.request.exc_info = None
        _exc_info.return_value = (None, None, None)
        exc_info = subscribers.get_exception_for_request(self.request)
        self.assertIs(exc_info, None)
        _exc_info.assert_called_once()

    def test_opbeat_tween_gets_response_if_no_error_occured(self):
        mock_response = {}

        handler = mock.MagicMock()
        handler.return_value = mock_response

        response = subscribers.opbeat_tween(
            handler,
            self.request.registry,
            self.request,
        )

        self.assertIs(response, mock_response)
        handler.assert_called_once_with(self.request)

    @mock.patch('sys.exc_info')
    @mock.patch('opbeat_pyramid.subscribers.handle_exception')
    def test_opbeat_tween_raises_handler_exceptions(self, handle_exc, mock):
        exc_info = mock.return_value = [None, ValueError()]

        handler = mock.MagicMock()
        handler.side_effect = exc_info[1]

        break_shit = functools.partial(
            subscribers.opbeat_tween,
            handler,
            self.request.registry,
            self.request,
        )

        self.assertRaises(ValueError, break_shit)
        handle_exc.assert_called_once_with(self.request, exc_info)

    @mock.patch('sys.exc_info')
    @mock.patch('opbeat_pyramid.subscribers.handle_exception')
    def test_opbeat_tween_raises_sys_exceptions(self, handle_exc, mock):
        e = ValueError()
        exc_info = mock.return_value = [type(e), e]

        handler = mock.MagicMock()
        handler.return_value = ''

        subscribers.opbeat_tween(handler, self.request.registry, self.request)

        handle_exc.assert_called_once_with(self.request, exc_info)

    def test_get_status_code_returns_status_code_from_response(self):
        code = 415
        self.request.response.status_code = code
        self.assertEqual(code, subscribers.get_status_code(self.request))

    def test_get_status_code_returns_exception_code_if_not_None(self):
        self.request.exc_info = [None, httpexceptions.HTTPNotFound()]
        self.assertEqual(404, subscribers.get_status_code(self.request))

    def test_get_route_name_uses_view_name_if_available(self):
        self.request.view_name = 'example.view'

        # Ensure these are set to ensure view_name is preferred
        self.request.matched_route.name = 'something_bad_happened'

        route_name = subscribers.get_route_name(self.request)
        self.assertIs(self.request.view_name, route_name)

    def test_get_route_name_uses_matched_route_if_available(self):
        route_name = subscribers.get_route_name(self.request)
        self.assertEqual('mock.example_view', route_name)

    def test_get_route_name_uses_unknown_route_name_setting_as_fallback(self):
        MOCK_UNKNOWN_ROUTE_NAME = 'Mock Unknown Route'

        self.request.view_name = None
        self.request.matched_route = None

        self.settings['opbeat.unknown_route_name'] = MOCK_UNKNOWN_ROUTE_NAME
        route_name = subscribers.get_route_name(self.request)
        self.assertEqual(route_name, MOCK_UNKNOWN_ROUTE_NAME)

    @mock.patch('opbeat_pyramid.subscribers.opbeat_tween')
    def test_opbeat_tween_factory_returns_a_curried_tween_function(self, mock):
        handler = {}

        registry = self.request.registry

        result = subscribers.opbeat_tween_factory(handler, registry)

        mock.assert_not_called()
        result(self.request)
        mock.assert_called_once_with(handler, registry, self.request)

    @mock.patch('opbeat.Client')
    def test_on_request_begin_starts_a_transaction(self, Client):
        client = mock.MagicMock()
        Client.return_value = client

        self.request.add_finished_callback = mock.MagicMock()

        mock_event = MockRequestEvent(self.request)
        subscribers.on_request_begin(mock_event)

        client.begin_transaction.assert_called_once()

        self.request.add_finished_callback.assert_called_once_with(
            subscribers.on_request_finished,
        )

    @mock.patch('opbeat.Client')
    def test_on_request_begin_is_a_noop_if_opbeat_disabled(self, Client):
        client = mock.MagicMock()
        Client.return_value = client

        self.settings['opbeat.enabled'] = False
        self.request.add_finished_callback = mock.MagicMock()

        mock_event = MockRequestEvent(self.request)
        subscribers.on_request_begin(mock_event)

        client.begin_transaction.assert_not_called()
        self.request.add_finished_callback.assert_not_called()

    @mock.patch('opbeat.Client')
    def test_on_request_finished_ends_the_current_transaction(self, Client):
        client = mock.MagicMock()
        Client.return_value = client

        self.request._opbeat_client = client

        client.end_transaction.assert_not_called()
        subscribers.on_request_finished(self.request)

        client.end_transaction.assert_called_once_with(
            'mock.example_view',
            200,
        )

    @mock.patch('opbeat.Client')
    def test_on_request_finished_does_nothing_if_disabled(self, Client):
        client = mock.MagicMock()
        Client.return_value = client

        client.end_transaction.assert_not_called()
        subscribers.on_request_finished(self.request)

        client.end_transaction.assert_not_called()
