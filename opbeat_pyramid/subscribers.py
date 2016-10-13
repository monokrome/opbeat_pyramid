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


def handle_exception(client, request):
    status_code = None

    if not request.exc_info:
        return status_code

    ex_value = request.exc_info[1]
    is_redirect = isinstance(ex_value, httpexceptions.HTTPRedirection)
    is_redirect_exception = ex_value and is_redirect

    if is_redirect_exception:
        return ex_value.code

    if isinstance(ex_value, httpexceptions.HTTPException):
        status_code = ex_value.code

    details = get_safe_settings(request.registry.settings)

    details.update({
        'url': request.url,
        'user_agent': request.user_agent,
        'client_ip_address': request.client_addr,
        'status_code': status_code,
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
    client.capture_exception(request.exc_info, data=data, extra=details)

    return status_code


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

    if request.exc_info:
        status_code = handle_exception(client, request)
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
