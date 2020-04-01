import ConfigParser
import logging
import os
import shutil
import sys
import unittest
import urllib2
import mock


class TestCase(unittest.TestCase):
    _patchers = []

    def setUp(self):
        super(TestCase, self).setUp()

        self._prepare_mocks()

        self.addCleanup(self.cleanup)

    def _prepare_mocks(self):
        self._mock_os = self._get_patched_mock(
            os,
            'encoder.os',
            'job.os'
        )
        self._mock_logging = self._get_patched_mock(logging, 'encoder.logging')
        self._prepare_config_mocks()
        self._mock_urllib2 = self._get_patched_mock(urllib2, 'api.urllib2')
        self._mock_shutil = self._get_patched_mock(shutil, 'job.shutil')

    def _prepare_config_mocks(self):
        self._mock_config_module = self._get_patched_mock(
            ConfigParser,
            'encoder.ConfigParser',
            'api.ConfigParser',
            'job.ConfigParser'
        )
        self._mock_config = self._build_mock(ConfigParser.ConfigParser)
        self._mock_config_module.ConfigParser.return_value = self._mock_config

    def _get_patched_mock(self, class_, *targets):
        mock_ = self._build_mock(class_)

        for target in targets:
            self._patch_target(target, mock_)

        return mock_

    @staticmethod
    def _build_mock(class_):
        return mock.MagicMock(spec_set=class_)

    def _patch_target(self, target, new):
        patcher = mock.patch(target, new=new)

        self._patchers.append(patcher)

        return patcher.start()

    def cleanup(self):
        for patcher in self._patchers:
            patcher.stop()
