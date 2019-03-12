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
import os

import charms.reactive as reactive
import charmhelpers.fetch as fetch
import charmhelpers.core.hookenv as hookenv
import charmhelpers.core.host as ch_host

import charmhelpers.contrib.network.ip

COROSYNC_DIR = '/etc/corosync/'
SERVICES = ['pacemaker_remote', 'pcsd']
PACKAGES = ['pacemaker-remote', 'pcs', 'resource-agents', 'corosync']
PACEMAKER_KEY = '/etc/pacemaker/authkey'


def install_packages():
    hookenv.status_set('maintenance', 'Installing packages')
    fetch.apt_install(PACKAGES, fatal=True)
    hookenv.status_set('maintenance',
                       'Installation complete - awaiting next status')


def wipe_corosync_state():
    try:
        shutil.rmtree('{}/uidgid.d'.format(COROSYNC_DIR))
    except FileNotFoundError:
        pass
    try:
        os.remove('{}/corosync.conf'.format(COROSYNC_DIR))
    except FileNotFoundError:
        pass


def restart_services():
    for svc in SERVICES:
        ch_host.service_restart(svc)


@reactive.when_not('pacemaker-remote.installed')
def install():
    install_packages()
    wipe_corosync_state()
    reactive.set_flag('pacemaker-remote.installed')


@reactive.when('endpoint.pacemaker-remote.joined')
def publish_stonith_info():
    if hookenv.config(''):
        remote = reactive.endpoint_from_flag(
            'endpoint.pacemaker-remote.joined')
        remote.publish_info(
            stonith_hostname=charmhelpers.contrib.network.ip.get_hostname(
                hookenv.unit_get('private-address')))


@reactive.when('endpoint.pacemaker-remote.changed.pacemaker-key')
def write_pacemaker_key():
    remote = reactive.endpoint_from_flag('endpoint.pacemaker-remote.changed')
    key = remote.get_pacemaker_key()
    if key:
        ch_host.write_file(
            PACEMAKER_KEY,
            key,
            owner='hacluster',
            group='haclient',
            perms=0o444)
        restart_services()
