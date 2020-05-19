# Overview

[Pacemaker Remote][upstream-pacemaker-remote] is a small daemon that allows a
host to be used as a Pacemaker node without running the full cluster stack.
The pacemaker-remote charm is a subordinate charm that deploys the daemon.

This charm can be used to help deploy [Masakari][upstream-masakari], which
provides automated recovery of KVM-based OpenStack machine instances. See the
[masakari][masakari-charm] charm for more information on that use case.

# Usage

## Configuration

See file `config.yaml` for the full list of configuration options, along with
their descriptions and default values.

## Deployment

To deploy pacemaker-remote:

    juju deploy pacemaker-remote

Because this is a subordinate charm a relation will need to be added to another
application to have the charm deployed on a machine.

# Bugs

Please report bugs on [Launchpad][lp-bugs-charm-pacemaker-remote].

For general charm questions refer to the [OpenStack Charm Guide][cg].

<!-- LINKS -->

[upstream-masakari]: https://docs.openstack.org/masakari
[upstream-pacemaker-remote]: https://clusterlabs.org/pacemaker/doc/en-US/Pacemaker/1.1/html-single/Pacemaker_Remote/
[cg]: https://docs.openstack.org/charm-guide
[cdg-app-ha-apps]: https://docs.openstack.org/project-deploy-guide/charm-deployment-guide/latest/app-ha.html#ha-applications
[lp-bugs-charm-pacemaker-remote]: https://bugs.launchpad.net/charm-pacemaker-remote/+filebug
[masakari-charm]: https://jaas.ai/masakari
