__VERSION__ = '1.0.8'


import pyramid.tweens


def includeme(config, module_name='opbeat_pyramid'):
    """ Extensibility function for using this module with any Pyramid app. """

    config.scan(module_name)

    config.add_tween(
        'opbeat_pyramid.subscribers.opbeat_tween_factory',
        over=[
            pyramid.tweens.EXCVIEW,
            # if pyramid_tm is in the pipeline we want to track errors caused
            # by commit/abort so we try to place ourselves over it
            'pyramid_tm.tm_tween_factory',
        ]
    )
