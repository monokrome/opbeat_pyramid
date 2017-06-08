__VERSION__ = '1.0.12'


def _should_ignore_module(module_name):
    return module_name.endswith('_spec')


def includeme(config, module_name='opbeat_pyramid'):
    """ Extensibility function for using this module with any Pyramid app. """

    config.scan(module_name, ignore=_should_ignore_module)
