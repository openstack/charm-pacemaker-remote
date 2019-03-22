# Copyright 2019 Canonical Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from __future__ import absolute_import
from __future__ import print_function

import unittest

import mock

import reactive.pacemaker_remote_handlers as handlers


_when_args = {}
_when_not_args = {}


def mock_hook_factory(d):

    def mock_hook(*args, **kwargs):

        def inner(f):
            # remember what we were passed.  Note that we can't actually
            # determine the class we're attached to, as the decorator only gets
            # the function.
            try:
                d[f.__name__].append(dict(args=args, kwargs=kwargs))
            except KeyError:
                d[f.__name__] = [dict(args=args, kwargs=kwargs)]
            return f
        return inner
    return mock_hook


class TestPAcemakerRemoteHandlers(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._patched_when = mock.patch('charms.reactive.when',
                                       mock_hook_factory(_when_args))
        cls._patched_when_started = cls._patched_when.start()
        cls._patched_when_not = mock.patch('charms.reactive.when_not',
                                           mock_hook_factory(_when_not_args))
        cls._patched_when_not_started = cls._patched_when_not.start()
        # force requires to rerun the mock_hook decorator:
        # try except is Python2/Python3 compatibility as Python3 has moved
        # reload to importlib.
        try:
            reload(handlers)
        except NameError:
            import importlib
            importlib.reload(handlers)

    @classmethod
    def tearDownClass(cls):
        cls._patched_when.stop()
        cls._patched_when_started = None
        cls._patched_when = None
        cls._patched_when_not.stop()
        cls._patched_when_not_started = None
        cls._patched_when_not = None
        # and fix any breakage we did to the module
        try:
            reload(handlers)
        except NameError:
            import importlib
            importlib.reload(handlers)

    def setUp(self):
        self._patches = {}
        self._patches_start = {}

    def tearDown(self):
        for k, v in self._patches.items():
            v.stop()
            setattr(self, k, None)
        self._patches = None
        self._patches_start = None

    def patch(self, obj, attr, return_value=None):
        mocked = mock.patch.object(obj, attr)
        self._patches[attr] = mocked
        started = mocked.start()
        started.return_value = return_value
        self._patches_start[attr] = started
        setattr(self, attr, started)

    def test_install_packages(self):
        self.patch(handlers.hookenv, 'status_set')
        self.patch(handlers.fetch, 'apt_install')
        handlers.install_packages()
        self.apt_install.assert_called_once_with(
            ['pacemaker-remote', 'pcs', 'resource-agents', 'corosync'],
            fatal=True)
        status_calls = [
            mock.call('maintenance', 'Installing packages'),
            mock.call(
                'maintenance', 'Installation complete - awaiting next status')]
        self.status_set.assert_has_calls(status_calls)

    def test_wipe_corosync_state(self):
        self.patch(handlers.shutil, 'rmtree')
        self.patch(handlers.os, 'remove')
        handlers.wipe_corosync_state()
        self.rmtree.assert_called_once_with('/etc/corosync/uidgid.d')
        self.remove.assert_called_once_with('/etc/corosync/corosync.conf')

    def test_wipe_corosync_state_noop(self):
        self.patch(handlers.shutil, 'rmtree')
        self.patch(handlers.os, 'remove')
        self.rmtree.side_effect = FileNotFoundError
        self.remove.side_effect = FileNotFoundError
        handlers.wipe_corosync_state()

    def test_restart_services(self):
        self.patch(handlers.ch_host, 'service_restart')
        handlers.restart_services()
        restart_calls = [
            mock.call('pacemaker_remote'),
            mock.call('pcsd')]
        self.service_restart.assert_has_calls(restart_calls)

    def test_install(self):
        self.patch(handlers.reactive, 'set_flag')
        self.patch(handlers, 'install_packages')
        self.patch(handlers, 'wipe_corosync_state')
        handlers.install()
        self.set_flag.assert_called_once_with('pacemaker-remote.installed')
        self.install_packages.assert_called_once_with()
        self.wipe_corosync_state.assert_called_once_with()

    def test_publish_stonith_info(self):
        self.patch(handlers.charmhelpers.contrib.network.ip, 'get_hostname')
        self.patch(handlers.hookenv, 'status_set')
        self.patch(handlers.hookenv, 'config')
        self.patch(handlers.hookenv, 'unit_get')
        self.patch(handlers.reactive, 'endpoint_from_flag')
        self.unit_get.return_value = '10.0.0.10'
        self.get_hostname.return_value = 'myhost.maas'
        cfg = {
            'enable-stonith': True,
            'enable-resources': True}
        self.config.side_effect = lambda x: cfg.get(x)
        endpoint_mock = mock.MagicMock()
        self.endpoint_from_flag.return_value = endpoint_mock
        handlers.publish_stonith_info()
        endpoint_mock.publish_info.assert_called_once_with(
            enable_resources=True,
            remote_hostname='myhost.maas',
            stonith_hostname='myhost.maas')

    def test_publish_stonith_info_all_off(self):
        self.patch(handlers.charmhelpers.contrib.network.ip, 'get_hostname')
        self.patch(handlers.hookenv, 'status_set')
        self.patch(handlers.hookenv, 'config')
        self.patch(handlers.hookenv, 'unit_get')
        self.patch(handlers.reactive, 'endpoint_from_flag')
        self.unit_get.return_value = '10.0.0.10'
        self.get_hostname.return_value = 'myhost.maas'
        cfg = {
            'enable-stonith': False,
            'enable-resources': False}
        self.config.side_effect = lambda x: cfg.get(x)
        endpoint_mock = mock.MagicMock()
        self.endpoint_from_flag.return_value = endpoint_mock
        handlers.publish_stonith_info()
        endpoint_mock.publish_info.assert_called_once_with(
            enable_resources=False,
            remote_hostname='myhost.maas',
            stonith_hostname=None)

    def test_write_pacemaker_key(self):
        self.patch(handlers.reactive, 'endpoint_from_flag')
        endpoint_mock = mock.MagicMock()
        endpoint_mock.get_pacemaker_key.return_value = 'corokey'
        self.endpoint_from_flag.return_value = endpoint_mock
        self.patch(handlers.hookenv, 'status_set')
        self.patch(handlers.ch_host, 'write_file')
        handlers.write_pacemaker_key()
        self.write_file.assert_called_once_with(
            '/etc/pacemaker/authkey',
            'corokey',
            group='haclient',
            owner='hacluster',
            perms=292)
        self.status_set.assert_called_once_with('active', 'Unit is ready')

    def test_write_pacemaker_key_nokey(self):
        self.patch(handlers.reactive, 'endpoint_from_flag')
        endpoint_mock = mock.MagicMock()
        endpoint_mock.get_pacemaker_key.return_value = None
        self.endpoint_from_flag.return_value = endpoint_mock
        self.patch(handlers.ch_host, 'write_file')
        handlers.write_pacemaker_key()
        self.assertFalse(self.write_file.called)

    def test_pacmaker_config_changed(self):
        self.patch(handlers, 'restart_services')
        handlers.pacmaker_config_changed()
        self.restart_services.assert_called_once_with()
