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

import shutil
import socket
import os

import charms.reactive as reactive
import charmhelpers.fetch as fetch
import charmhelpers.core.hookenv as hookenv
import charmhelpers.core.host as ch_host

COROSYNC_DIR = '/etc/corosync'
SERVICES = ['pacemaker_remote', 'pcsd']
PACKAGES = ['pacemaker-remote', 'pcs', 'resource-agents', 'corosync']
PACEMAKER_KEY = '/etc/pacemaker/authkey'


def install_packages():
    """Install apckages neede dby charm"""
    hookenv.status_set('maintenance', 'Installing packages')
    fetch.apt_install(PACKAGES, fatal=True)
    hookenv.status_set('maintenance',
                       'Installation complete - awaiting next status')


def wipe_corosync_state():
    """Remove state left by corosync package"""
    try:
        shutil.rmtree('{}/uidgid.d'.format(COROSYNC_DIR))
    except FileNotFoundError:
        pass
    try:
        os.remove('{}/corosync.conf'.format(COROSYNC_DIR))
    except FileNotFoundError:
        pass


def restart_services():
    """Restart pacemker_remote and associated services"""
    for svc in SERVICES:
        ch_host.service_restart(svc)


@reactive.when_not('pacemaker-remote.installed')
def install():
    """Perform initial setup of pacmekaer-remote"""
    install_packages()
    wipe_corosync_state()
    reactive.set_flag('pacemaker-remote.installed')


@reactive.when('endpoint.pacemaker-remote.joined')
def publish_stonith_info():
    """Provide remote hacluster with info for including remote in cluster"""
    remote_ip = hookenv.network_get_primary_address('pacemaker-remote')
    remote_hostname = socket.gethostname()
    if hookenv.config('enable-stonith'):
        stonith_hostname = remote_hostname
    else:
        stonith_hostname = None
    remote = reactive.endpoint_from_flag(
        'endpoint.pacemaker-remote.joined')
    remote.publish_info(
        remote_hostname=remote_hostname,
        remote_ip=remote_ip,
        enable_resources=hookenv.config('enable-resources'),
        stonith_hostname=stonith_hostname)


@reactive.when_file_changed(PACEMAKER_KEY)
def pacmaker_config_changed():
    """Restart all seervices managed by the charm."""
    restart_services()


@reactive.when('endpoint.pacemaker-remote.changed.pacemaker-key')
def write_pacemaker_key():
    """Finish setup of pacemaker-remote"""
    remote = reactive.endpoint_from_flag('endpoint.pacemaker-remote.changed')
    key = remote.get_pacemaker_key()
    if key:
        ch_host.write_file(
            PACEMAKER_KEY,
            key,
            owner='hacluster',
            group='haclient',
            perms=0o444)
        hookenv.status_set('active', 'Unit is ready')
