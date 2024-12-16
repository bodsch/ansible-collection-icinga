#!/usr/bin/python3

# -*- coding: utf-8 -*-

# (c) 2020, Bodo Schulz <bodo@boone-schulz.de>
# BSD 2-clause (see LICENSE or https://opensource.org/licenses/BSD-2-Clause)

from __future__ import absolute_import, division, print_function
import os

from ansible.module_utils.basic import AnsibleModule


__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: icingaweb_themes
author:
    - 'Bodo Schulz'
short_description: enable / disable icingaweb modules.
description: ''
"""

EXAMPLES = """
- name: disable modules
  become: true
  icingaweb_themes:
    state: absent
    module: dark_lord
"""

# ---------------------------------------------------------------------------------------


class IcingaWeb2Themes(object):
    """
    Main Class to implement the Icinga2 API Client
    """
    module = None

    def __init__(self, module):
        """
          Initialize all needed Variables
        """
        self.module = module

        self.state = module.params.get("state")
        self.install_directory = module.params.get("install_directory")
        self.themes = module.params.get("themes")
        self.checksums = module.params.get("checksums")

    def run(self):
        res = dict(
            changed=False,
            failed=False,
        )

        if os.path.isdir(self.install_directory):
            """
            """
            changed = False

            if len(self.themes) > 0 and len(self.checksums) > 0:
                """
                """

                _themes = self.themes.copy()

                for theme in _themes:
                    checksum = None
                    theme_checksum = None

                    checksum_file = os.path.join(
                        self.install_directory,
                        theme,
                        ".checksum"
                    )

                    self.module.log(msg="- checksum_file : '{}'".format(checksum_file))

                    if os.path.exists(checksum_file):
                        with open(checksum_file) as f:
                            checksum = f.readlines()[0]

                        if checksum is not None:
                            theme_checksum = self.checksums.get(theme, {}).get("checksum")

                        theme_version = _themes.get(theme, {}).get("version")
                        installed_version = self.checksums.get(theme, {}).get("version")

                        version_compare_git = theme_version in ["master", "main"]
                        version_compare = theme_version != installed_version
                        checksum_compare = (checksum is not None and theme_checksum is not None and theme_checksum == checksum)

                        if version_compare_git:
                            self.themes[theme]['download'] = True
                            changed = True
                        else:
                            if not version_compare and not checksum_compare:
                                self.themes[theme]['download'] = True
                                changed = True
                            else:
                                self.themes[theme]['download'] = False
                    else:
                        self.themes[theme]['download'] = True
                        changed = True
            else:
                _themes = self.themes.copy()

                for theme in _themes:
                    self.themes[theme]['download'] = True
                    changed = True

            res['changed'] = changed
            res['themes'] = self.themes
        else:
            msg = "{} is no directory".format(self.install_directory)

            res['ansible_module_results'] = msg
            res['failed'] = True
            module.log(msg=msg)

        return res


# ===========================================
# Module execution.
#


def main():
    global module
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(
                default="verify",
                choices=["verify", "absent", "present"]
            ),
            install_directory=dict(
                required=True,
                type="path"
            ),
            themes=dict(
                required=True,
                type=dict
            ),
            checksums=dict(
                required=True,
                type=dict
            ),
        ),
        supports_check_mode=False,
    )

    icingaweb = IcingaWeb2Themes(module)
    result = icingaweb.run()

    module.log(msg="= result : '{}'".format(result))

    module.exit_json(**result)


# import module snippets
if __name__ == '__main__':
    main()
