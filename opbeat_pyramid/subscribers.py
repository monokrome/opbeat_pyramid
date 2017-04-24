import sys

import opbeat

from opbeat.instrumentation import control

from pyramid import events
from pyramid import httpexceptions


CLIENTS = {}
DEFAULT_UNSAFE_SETTINGS_TERMS = 'token,password,passphrase,secret,private,key'


control.instrument()


def opbeat_client_factory(request):
    app_id = request.registry.settings['opbeat.app_id']

    if app_id not in CLIENTS:
        secret_token = request.registry.settings['opbeat.secret_token']
        organization_id = request.registry.settings['opbeat.organization_id']

        CLIENTS[app_id] = opbeat.Client(
            secret_token=secret_token,
            organization_id=organization_id,
            app_id=app_id,
        )

    return CLIENTS[app_id]


def is_opbeat_enabled(request):
    setting = request.registry.settings.get('opbeat.enabled', False)
    return setting is True or setting == 'true'


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


def handle_exception(request, exc_info=None):
    # Save the traceback as it may get lost when we get the message.
    # handle_exception is not in the traceback, so calling sys.exc_info
    # does NOT create a circular reference
    if exc_info is None:
        exc_info = sys.exc_info()

    if exc_info[1] and isinstance(exc_info[1], httpexceptions.HTTPException):
        # Ignore any exceptions like 404 and 302s
        return

    try:
        details = get_safe_settings(request.registry.settings)

        details.update({
            'url': request.url,
            'user_agent': request.user_agent,
            'client_ip_address': request.client_addr,
        })

        scheme = request.scheme + '://'
        host = request.host + ':' + request.host_port
        path = request.path

        data = {
            'http': {
                'url': scheme + host + path,
                'method': request.method,
                'query_string': request.query_string,
            }
        }

        client = opbeat_client_factory(request)
        client.capture_exception(exc_info, data=data, extra=details)
    except:
        # Exceptions in exception logging should be ignored
        pass

    return

def opbeat_tween_factory(handler, registry):
    def opbeat_tween(request):
        try:
            response = handler(request)
            exc_info = getattr(request, 'exc_info', None)
            if exc_info is not None:
                handle_exception(request, exc_info)
            return response

        except:
            handle_exception(request)
            raise
    return opbeat_tween

def on_request_finished(request):
    if not is_opbeat_enabled(request):
        return

    client = opbeat_client_factory(request)
    module_name = get_request_module_name(request)

    if request.matched_route and request.matched_route.name:
        route_name = module_name + '.' + request.matched_route.name
    elif request.view_name:
        route_name = request.view_name
    else:
        route_name = 'Unknown Route'

    status_code = None

    if request.exc_info:
        if request.exc_info[1] and \
           isinstance(request.exc_info[1], httpexceptions.HTTPException):
            status_code = request.exc_info[1].code
    else:
        status_code = request.response.status_code

    client.end_transaction(route_name, status_code)


@events.subscriber(events.NewRequest)
def on_request_begin(event):
    request = event.request

    if not is_opbeat_enabled(request):
        return

    client = opbeat_client_factory(request)
    client.begin_transaction(get_request_module_name(request))
    request.add_finished_callback(on_request_finished)
