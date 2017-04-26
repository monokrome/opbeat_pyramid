import venusian


class tween_config(object):
    """ A decorator which allows developers to annotate tween factories. """

    venusian = venusian

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, wrapped_tween_factory):
        def do_the_thing(context, name, obj):
            module_name = wrapped_tween_factory.__module__
            callable_name = wrapped_tween_factory.__name__
            factory_string = module_name + '.' + callable_name

            context.config.with_package(info.module).add_tween(
                factory_string,
                *self.args,
                **self.kwargs
            )

        info = self.venusian.attach(
            wrapped_tween_factory,
            do_the_thing,
            category='opbeat_pyramid',
        )

        return wrapped_tween_factory
