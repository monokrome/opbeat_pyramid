import mock
import unittest

from opbeat_pyramid import tweens


class OpbeatSubscribersTestCase(unittest.TestCase):
    @mock.patch('venusian.attach')
    def test_tween_returns_original_wrapped_object(self, attach):
        handler = mock.MagicMock()
        wrapped = tweens.tween_config()(handler)

        handler.assert_not_called()
        self.assertIs(wrapped, handler)

    @mock.patch('venusian.attach')
    @mock.patch('opbeat_pyramid.tweens.tween_config.configure')
    def test_tween_attaches_configure_to_venusian(self, configure, attach):
        handler = mock.MagicMock()
        tweens.tween_config()(handler)

        attach.assert_called_once()

        call_args = attach.call_args[0]
        self.assertIs(handler, call_args[0])

        configure.assert_not_called()
        call_args[1]()
        configure.assert_called_once_with(handler)

    def test_configure_actually_configures_a_tween(self):
        MOCK_MODULE = 'mock_module'

        mock_args = [1, 2, 3]
        mock_kwargs = {'mock': 'kwarg'}

        config = tweens.tween_config(*mock_args, **mock_kwargs)
        config.info = mock.MagicMock()  # Mock out venusian info
        config.info.module = MOCK_MODULE

        context = mock.MagicMock()
        config_instance = mock.MagicMock()
        context.config.with_package.return_value = config_instance

        factory = mock.MagicMock()
        obj = mock.MagicMock()

        factory.__module__ = MOCK_MODULE
        factory.__name__ = 'factory'

        config.configure(factory, context, 'example', obj)

        config_instance.add_tween.assert_called_once_with(
            'mock_module.factory',
            *mock_args,
            **mock_kwargs
        )
