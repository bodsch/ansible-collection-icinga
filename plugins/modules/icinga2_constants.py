#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# (c) 2020-2022, Bodo Schulz <bodo@boone-schulz.de>
# BSD 2-clause (see LICENSE or https://opensource.org/licenses/BSD-2-Clause)
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import absolute_import, division, print_function

from ansible.module_utils.basic import AnsibleModule

import socket


class Icinga2Constants(object):
    """
    """
    module = None

    def __init__(self, module):
        """
        """
        self.module = module

        self.icinga2_version = module.params.get("icinga2_version")
        self.constants = module.params.get("constants")
        self.owner = module.params.get("owner")
        self.group = module.params.get("group")

        self.contants_file = "/etc/icinga2/constants.conf"

    def run(self):
        """
          runner
        """
        result = dict(
            failed=False,
            changed=False,
            ansible_module_results="none"
        )

        hostname = socket.gethostname()
        fqdn = socket.getfqdn()

        self.module.log(msg=f"hostname: {hostname}")
        self.module.log(msg=f"fqdn    : {fqdn}")

        return result


def main():

    args = dict(
        icinga2_version=dict(
            required=True,
            type=str
        ),
        constants=dict(
            required=True,
            type=dict
        ),
        owner=dict(
            required=True,
            type=str
        ),
        group=dict(
            required=True,
            type=str
        ),
    )

    module = AnsibleModule(
        argument_spec=args,
        supports_check_mode=True,
    )

    icinga = Icinga2Constants(module)
    result = icinga.run()

    module.log(msg=f"= result: {result}")

    module.exit_json(**result)


# import module snippets
if __name__ == '__main__':
    main()
