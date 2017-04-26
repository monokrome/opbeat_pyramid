import functools

import venusian


class tween_config(object):
    """ A decorator which allows developers to annotate tween factories. """

    venusian = venusian

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.info = None

    def configure(self, tween_factory, context, name, obj):
        # Reset info just in case something funky happens.
        info = self.info
        self.info = None

        module_name = tween_factory.__module__
        callable_name = tween_factory.__name__
        factory_string = module_name + '.' + callable_name

        context.config.with_package(info.module).add_tween(
            factory_string,
            *self.args,
            **self.kwargs
        )

    def __call__(self, tween_factory):
        self.info = self.venusian.attach(
            tween_factory,
            functools.partial(self.configure, tween_factory),
            category='opbeat_pyramid',
        )

        return tween_factory
