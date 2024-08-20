#!/usr/bin/python3
# -*- coding: utf-8 -*-

# (c) 2020-2022, Bodo Schulz <bodo@boone-schulz.de>
# BSD 2-clause (see LICENSE or https://opensource.org/licenses/BSD-2-Clause)
# SPDX-License-Identifier: BSD-2-Clause

from __future__ import absolute_import, division, print_function
import re

from ansible.module_utils.basic import AnsibleModule


class IcingaDbVersion(object):
    """
      Main Class
    """
    module = None

    def __init__(self, module):
        """
          Initialize all needed Variables
        """
        self.module = module

        self._icingadb = module.get_bin_path('icingadb', True)

    def run(self):
        """
          runner
        """
        result = dict(
            rc=127,
            failed=True,
            changed=False,
        )

        args = []
        args.append(self._icingadb)
        args.append("--version")

        self.module.log(msg=f"  args: '{args}'")

        rc, out, err = self._exec(args, False)

        version_string = "unknown"

        pattern = re.compile(r"Icinga.*version: v(?P<version>.*).*")

        version = re.search(pattern, out)

        if version:
            version_string = version.group('version')

        result['rc'] = rc

        if rc == 0:
            result['failed'] = False
            result['version'] = version_string

        return result

    def _exec(self, commands, check_rc=True):
        """
          execute shell program
        """
        rc, out, err = self.module.run_command(commands, check_rc=check_rc)

        self.module.log(msg=f"  rc : '{rc}'")
        self.module.log(msg=f"  out: '{out}'")
        self.module.log(msg=f"  err: '{err}'")

        return rc, out, err


# ===========================================
# Module execution.
#


def main():

    module = AnsibleModule(
        argument_spec=dict(
        ),
        supports_check_mode=True,
    )

    icinga = IcingaDbVersion(module)
    result = icinga.run()

    module.log(msg=f"= result: {result}")

    module.exit_json(**result)


# import module snippets
if __name__ == '__main__':
    main()
