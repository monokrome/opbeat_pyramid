import mock
import unittest

import opbeat_pyramid


class OpbeatSubscribersTestCase(unittest.TestCase):
    def test_should_ignore_module_does_not_ignore_by_default(self):
        self.assertFalse(opbeat_pyramid._should_ignore_module(
            'opbeat_pyramid.subscribers',
        ))

    def test_includeme_scans_with_the_expected_arguments(self):
        config = mock.MagicMock()
        opbeat_pyramid.includeme(config)

        config.scan.assert_called_once()
        config.scan.assert_called_with(
            opbeat_pyramid.__name__,
            ignore=opbeat_pyramid._should_ignore_module,
        )
