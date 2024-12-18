#!/usr/bin/python3
# -*- coding: utf-8 -*-

# (c) 2020-2022, Bodo Schulz <bodo@boone-schulz.de>
# BSD 2-clause (see LICENSE or https://opensource.org/licenses/BSD-2-Clause)
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import absolute_import, division, print_function

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: icinga2_ticket
author: Bodo Schulz (@bodsch)
version_added: 1.0.0

short_description: TBD
description: ''

options:
  common_name:
    description: TBD
    required: true
    type: str

  salt:
    description: TBD
    required: true
    type: str
"""

EXAMPLES = """
- name: "create a ticket from icinga2 master for the secondary master '{{ ansible_fqdn }}'"
  delegate_to: "{{ icinga2_primary_master }}"
  bodsch.icinga.icinga2_ticket:
    common_name: "{{ icinga2_certificate_cn }}"
    salt: "{{ icinga2_salt }}"
  register: ticket

- name: "create a pki ticket at '{{ icinga2_primary_master }}'"
  bodsch.icinga.icinga2_ticket:
    common_name: "{{ icinga2_certificate_cn }}"
    salt: "{{ icinga2_salt }}"
  register: ticket
  delegate_to: "{{ icinga2_primary_master }}"
"""

RETURN = r"""
"""

# ---------------------------------------------------------------------------------------


class Icinga2TicketHelper(object):
    """
    Main Class to implement the Icinga2 API Client
    """
    module = None

    def __init__(self, module):
        """
          Initialize all needed Variables
        """
        self.module = module

        self.common_name = module.params.get("common_name")
        self.salt = module.params.get("salt")

        self._icinga2 = module.get_bin_path('icinga2', True)

    def run(self):
        """
          runner
        """
        result = dict(
            failed=False,
            changed=False,
            ansible_module_results="none"
        )

        # Generates an Icinga 2 ticket
        self.module.log(msg="Generates an Icinga 2 ticket.")

        args = [self._icinga2]
        args.append("pki")
        args.append("ticket")
        args.append("--cn")
        args.append(self.common_name)
        args.append("--salt")
        args.append(self.salt)

        rc, out = self._exec(args)

        result['ticket'] = f"{out.rstrip()}"

        if rc == 0:
            result['changed'] = True
        else:
            result['failed'] = True

        return result

    def _exec(self, commands):
        """
          execute shell program
        """
        rc, out, err = self.module.run_command(commands, check_rc=True)
        return rc, out


# ===========================================
# Module execution.
#


def main():

    module = AnsibleModule(
        argument_spec=dict(
            common_name=dict(required=True),
            salt=dict(required=True)
        ),
        supports_check_mode=True,
    )

    icinga = Icinga2TicketHelper(module)
    result = icinga.run()

    module.log(msg=f"= result: {result}")

    module.exit_json(**result)


# import module snippets
if __name__ == '__main__':
    main()
