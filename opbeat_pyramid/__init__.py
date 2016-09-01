__VERSION__ = '1.0.2'


def includeme(config, module_name='opbeat_pyramid'):
    """ Extensibility function for using this module with any Pyramid app. """

    config.scan(module_name)
