import logging
import functools
import opbeat
import os
import sys


import pyramid.tweens

from opbeat.instrumentation import control

from pyramid import events
from pyramid import httpexceptions
from pyramid.settings import asbool

from opbeat_pyramid import tweens


NO_DEFAULT_PROVIDED = {}
DEFAULT_UNKNOWN_ROUTE_TEXT = 'Unknown Route'
TRUTHY_VALUES = {True, 'true', 'yes', 'on'}

DEFAULT_UNSAFE_SETTINGS_TERMS = 'token,password,passphrase,secret,private,key'
OPBEAT_SETTING_PREFIX = 'opbeat.'


control.instrument()


logger = logging.getLogger(__name__)


def get_opbeat_setting(request, name, default=NO_DEFAULT_PROVIDED):
    setting_name = OPBEAT_SETTING_PREFIX + name

    environment_override = os.environ.get(setting_name.replace('.', '_').upper())
    if environment_override:
        return environment_override

    result = request.registry.settings.get(setting_name, default)

    if result is NO_DEFAULT_PROVIDED:
        raise ValueError('Setting ' + setting_name + ' is required.')

    return result


def get_opbeat_client_cache(request):
    if not hasattr(request.registry, '_opbeat_clients'):
        request.registry._opbeat_clients = {}

    return request.registry._opbeat_clients


def create_opbeat_client(request, app_id):
    secret_token = get_opbeat_setting(request, 'secret_token')
    organization_id = get_opbeat_setting(request, 'organization_id')

    return opbeat.Client(
        secret_token=secret_token,
        organization_id=organization_id,
        app_id=app_id,
    )


def opbeat_client_factory(request):
    clients = get_opbeat_client_cache(request)

    app_id = get_opbeat_setting(request, 'app_id')
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
    return get_opbeat_setting(request, 'module_name', default='UNKNOWN_MODULE')


def get_unsafe_settings_terms(request):
    private_terms = get_opbeat_setting(
        request,
        'unsafe_setting_terms',
        default=None,
    )

    if private_terms is None:
        return DEFAULT_UNSAFE_SETTINGS_TERMS

    return set(private_terms.split(','))


def get_safe_settings(request):
    unsafe_terms = get_unsafe_settings_terms(request)
    result = {}

    for key in request.registry.settings.keys():
        for term in unsafe_terms:
            if term in key:
                continue

        result[key] = request.registry.settings[key]

    return result


def should_ignore_exception(request, exc):
    ignore_setting = asbool(get_opbeat_setting(request, 'ignore_http_exceptions', default=False))
    if ignore_setting and is_http_exception(exc):
        return True
    return False


def capture_exception(request, exc_info, extra):
    client = opbeat_client_factory(request)

    data = {
        'http': {
            'url': get_full_request_url(request),
            'method': request.method,
            'query_string': request.query_string,
        }
    }

    try:
        return client.capture_exception(exc_info, data=data, extra=extra)

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

    details = get_safe_settings(request)

    details.update({
        'client_ip_address': request.client_addr,
        'logging_successful': 'true',
        'url': request.url,
        'user_agent': request.user_agent,
    })

    logger.error('An error occured. Sending to opbeat.', exc_info=exc_info)
    return capture_exception(request, exc_info, details)


def get_exception_for_request(request):
    exc_info = getattr(request, 'exc_info', None)

    if exc_info is not None:
        return exc_info

    return sys.exc_info()


def opbeat_tween(handler, registry, request):
    try:
        response = handler(request)
    except Exception as exc:
        handle_exception(request, sys.exc_info())
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
    if exc_info and exc_info[1]:
        exc_info = exc_info[1]

    return isinstance(exc_info, httpexceptions.HTTPException)


def get_status_code(request):
    # Handles an edge-case where `request.response` isn't the actual response.
    # This can occur whenever a view needs to create a new response instead of
    # using the one attached to the request.
    if is_http_exception(request.exc_info):
        return request.exc_info[1].code

    return request.response.status_code


def get_route_name(request):
    if request.view_name:
        return request.view_name

    elif request.matched_route and request.matched_route.name:
        module_name = get_request_module_name(request)
        return module_name + '.' + request.matched_route.name

    return get_opbeat_setting(
        request,
        'unknown_route_name',
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

    if not is_opbeat_enabled(request):
        return

    client = opbeat_client_factory(request)
    client.begin_transaction(get_request_module_name(request))
    request.add_finished_callback(on_request_finished)
