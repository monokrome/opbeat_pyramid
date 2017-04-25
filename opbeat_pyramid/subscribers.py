import functools
import opbeat
import sys

import pyramid.tweens

from opbeat.instrumentation import control

from pyramid import events
from pyramid import httpexceptions

from opbeat_pyramid import tweens


DEFAULT_UNKNOWN_ROUTE_TEXT = 'Unknown Route'
TRUTHY_VALUES = {True, 'true', 'yes', 'on'}

IGNORE_HTTP_EXCEPTIONS_SETTING = 'opbeat.ignore_http_exceptions'
DEFAULT_UNSAFE_SETTINGS_TERMS = 'token,password,passphrase,secret,private,key'


control.instrument()


def get_opbeat_client_cache(request):
    if not hasattr(request.registry, '_opbeat_clients'):
        request.registry._opbeat_clients = {}

    return request.registry._opbeat_clients


def create_opbeat_client(request, app_id):
    secret_token = request.registry.settings['opbeat.secret_token']
    organization_id = request.registry.settings['opbeat.organization_id']

    return opbeat.Client(
        secret_token=secret_token,
        organization_id=organization_id,
        app_id=app_id,
    )


def opbeat_client_factory(request):
    clients = get_opbeat_client_cache(request)

    # TODO: Handle case where this is unset / empty
    app_id = request.registry.settings['opbeat.app_id']
    client = clients.get(app_id)

    if client:
        return client

    clients[app_id] = create_opbeat_client(request, app_id)

    return clients[app_id]


def setting_is_enabled(request, setting_name):
    setting = request.registry.settings.get(setting_name, False)

    if setting is True:
        return True

    return setting.lower() in TRUTHY_VALUES


def is_opbeat_enabled(request):
    'opbeat.enabled'

def get_request_module_name(request):
    return request.registry.settings.get(
        'opbeat.module_name',
        'UNKNOWN_MODULE',
    )


def get_unsafe_settings_terms(settings):
    private_terms = settings.get('opbeat.unsafe_setting_terms', None)

    if private_terms is None:
        return DEFAULT_UNSAFE_SETTINGS_TERMS

    return set(private_terms.split(','))


def get_safe_settings(settings):
    unsafe_terms = get_unsafe_settings_terms(settings)
    result = {}

    for key in settings.keys():
        for term in unsafe_terms:
            if term in key:
                continue

        result[key] = settings[key]

    return result


def should_ignore_exception(request, exc_info):
    if not is_http_exception(exc_info):
        return False

    return request.registry.settings.get(IGNORE_HTTP_EXCEPTIONS_SETTING, False)


def capture_exception(exc_info, extra):
    client = opbeat_client_factory(request)

    data = {
        'http': {
            'url': get_full_request_url(request),
            'method': request.method,
            'query_string': request.query_string,
        }
    }

    try:
        return client.capture_exception(exc_info, data=data, extra=details)

    except Exception as e:
        # NOTE: This should not be allowed until we know which exception we are
        # looking for here.
        pass


def get_full_request_url(request):
    """ Get the full URL for a given request. """

    scheme = request.scheme + '://'
    host = request.host + ':' + request.host_port
    path = request.path
    return scheme + host + path


def handle_exception(request, exc_info):
    if should_ignore_exception(request, exc_info):
        return

    details = get_safe_settings(request.registry.settings)

    details.update({
        'client_ip_address': request.client_addr,
        'logging_successful': 'true',
        'url': request.url,
        'user_agent': request.user_agent,
    })

    return capture_exception(exc_info, details)


def get_exception_for_request(request):
    exc_info = getattr(request, 'exc_info', None)

    if exc_info is not None:
        return exc_info

    return sys.exc_info()


def opbeat_tween(handler, registry, request):
    try:
        response = handler(request)
    except Exception as exc:
        handle_exception(request, exc)
        raise

    exc_info = get_exception_for_request(request)

    if exc_info is not None:
        handle_exception(request, exc_info)

    return response


@tweens.tween_config(over=[
    pyramid.tweens.EXCVIEW,
    'pyramid_tm.tm_tween_factory',
])
def opbeat_tween_factory(handler, registry):
    return functools.partial(opbeat_tween, handler, registry)


def is_http_exception(exc_info):
    if not exc_info and not exc_info[1]:
        return False

    return isinstance(request.exc_info[1], httpexceptions.HTTPException)


def get_status_code(request):
    if is_http_exception(request.exc_info):
        return request.exc_info[1].code

    return request.response.status_code


def get_route_name(request):
    if request.view_name:
        return request.view_name

    elif request.matched_route and request.matched_route.name:
        module_name = get_request_module_name(request)
        return module_name + '.' + request.matched_route.name

    return request.registry.settings.get(
        'opbeat.unknown_route_name',
        DEFAULT_UNKNOWN_ROUTE_TEXT,
    )


def on_request_finished(request):
    if not is_opbeat_enabled(request):
        return

    client = opbeat_client_factory(request)
    client.end_transaction(get_route_name(request), get_status_code(request))


@events.subscriber(events.NewRequest)
def on_request_begin(event):
    request = event.request

    if is_opbeat_enabled(request):
        client = opbeat_client_factory(request)
        client.begin_transaction(get_request_module_name(request))
        request.add_finished_callback(on_request_finished)
