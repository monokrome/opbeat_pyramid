__VERSION__ = '1.0.8'


def includeme(config, module_name='opbeat_pyramid'):
    """ Extensibility function for using this module with any Pyramid app. """

    config.scan(module_name)

    # TODO: Is there a decorator for this?
    config.add_tween(
        'opbeat_pyramid.subscribers.opbeat_tween_factory',
        over=[
            'pyramid.tweens.EXCVIEW',
            'pyramid_tm.tm_tween_factory',
        ]
    )
