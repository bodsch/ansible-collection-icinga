#!/usr/bin/env python3

# -*- coding: utf-8 -*-

# (c) 2020, Bodo Schulz <bodo@boone-schulz.de>
# BSD 2-clause (see LICENSE or https://opensource.org/licenses/BSD-2-Clause)

from __future__ import absolute_import, print_function
import os

from packaging.version import Version, parse as parseVersion

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.bodsch.icinga.plugins.module_utils.icinga_database import IcingaDatabase

__metaclass__ = type


DOCUMENTATION = """
---
module: icingadb_database_update.py
author:
    - 'Bodo Schulz'
short_description: handle database updates for icingawdb.
description: ''
"""

EXAMPLES = """
- name: update database version information
  bodsch.icinga.icingadb_database_update:
    database_login_host: "{{ icingadb_database.host }}"
    database_login_user: "{{ icingadb_database.user }}"
    database_login_password: "{{ icingadb_database.password }}"
    database_name: "{{ icingadb_database.database }}"
    database_config_file: ""
    icingadb_version: "{{ ansible_local.icingadb.version }}"
    icingadb_upgrade_directory: "{{ icingadb_upgrade_directory }}"
  register: _icingadb_database_update
"""

# TODO
#  progamm_version vs. Database_version
#  1.0.0 = 3
#  1.1.0 = 4
#  1.1.1 = 5


class IcingaDbDatabaseUpdate(object):
    """
      Main Class
    """
    module = None

    def __init__(self, module):
        """
          Initialize all needed Variables
        """
        self.module = module

        self.database_name = module.params.get("database_name")
        self.database_config_file = module.params.get("database_config_file")
        self.database_login_host = module.params.get("database_login_host")
        self.database_login_port = module.params.get("database_login_port")
        self.database_login_socket = module.params.get("database_login_unix_socket")
        self.database_login_user = module.params.get("database_login_user")
        self.database_login_password = module.params.get("database_login_password")
        self.icingadb_version = module.params.get("icingadb_version")
        self.icingadb_upgrade_directory = module.params.get("icingadb_upgrade_directory")

        self.database_table_name = "icingadb_schema"
        self.db_autocommit = True
        self.db_connect_timeout = 30

        self.state_directory = "/etc/icingadb/.ansible"

        try:
            # Create target Directory
            os.mkdir(self.state_directory)
        except OSError:
            pass

    def run(self):
        """
        """
        _changed = False
        _failed = False
        _msg = "module init."

        self.icinga_database = IcingaDatabase(
            self.module,
            hostname=self.database_login_host,
            port=self.database_login_port,
            socket=self.database_login_socket,
            config_file=self.database_config_file
        )

        self.icinga_database.db_credentials(
            db_username=self.database_login_user,
            db_password=self.database_login_password,
            db_schema_name=self.database_name
        )

        (db_connect_error, db_message) = self.icinga_database.db_connect()
        if db_connect_error:
            return dict(
                failed=True,
                msg=db_message
            )

        # step two:
        # check current version
        (curr_version, db_error, message) = self.icinga_database.current_version(self.database_table_name)

        if db_error:
            return dict(
                failed=True,
                msg=message
            )

        curr_version = self.version_string(curr_version)

        self.module.log(f"Database version: is {curr_version} to should be {self.icingadb_version}.")

        if not curr_version:
            (state, db_error, message) = self.__update_version(version=self.icingadb_version)

            if db_error:
                _failed = True
                _msg = message

            if state:
                _changed = True
                _msg = "version successful updated."
        else:
            # version compare
            if Version(curr_version) == Version(self.icingadb_version):
                # self.module.log("versions equal.")
                return dict(
                    changed=False,
                    failed=False,
                    msg="icingaweb database is up to date."
                )

            elif Version(curr_version) < Version(self.icingadb_version):
                self.module.log(f"upgrade to version {self.icingadb_version} needed.")
                (state, db_error, message) = self.upgrade_database(from_version=curr_version)

                if db_error:
                    _failed = True

                if state:
                    _changed = True

                _msg = message

            else:
                return dict(
                    changed=False,
                    failed=False,
                    msg=f"icingaweb database downgrade are not supported. (current version are {curr_version})"
                )

        return dict(
            changed=_changed,
            failed=_failed,
            msg=_msg
        )

    def version_string(self, db_version):
        """
        """
        if int(db_version) == 3:
            return "1.0.0"
        elif int(db_version) == 4:
            return "1.1.0"
        elif int(db_version) == 5:
            return "1.1.1"
        else:
            return None

    def upgrade_database(self, from_version="1.0.0"):
        """
        """
        state = False
        db_error = False
        result_state = {}

        upgrade_files = self.__read_database_upgrades(from_version=from_version)

        for upgrade in upgrade_files:
            """
            """
            file_name = os.path.basename(upgrade)
            file_version = file_name.replace(".sql", "")

            result_state[str(file_version)] = {}
            self.module.log(msg=f"upgrade database to version: {file_version}")

            state = False
            db_error = False

            state, msg = self.icinga_database.db_import_sqlfile(
                sql_file=upgrade,
                close_cursor=True
            )

            result_state[file_version].update({
                "failed": state,
                "msg": msg
            })

            if state:
                break

        failed = (len({k: v for k, v in result_state.items() if v.get('failed', False)}) > 0)

        if failed:
            state = False

        return (state, db_error, result_state)

    def __read_database_upgrades(self, from_version="1.0.0"):
        """
        """
        _versions = []
        upgrade_files = []
        upgrade_versions = []

        for root, dirs, files in os.walk(self.icingadb_upgrade_directory, topdown=False):
            if files:
                _versions = files

        for v in _versions:
            """
            """
            version_string = v.replace(".sql", "")

            if version_string.startswith("1.0.0") or Version(version_string) <= Version(from_version):
                continue
            if Version(version_string) > Version(from_version) or Version(version_string) <= Version(self.icingadb_version):
                upgrade_versions.append(version_string)

        # version sort
        upgrade_versions.sort(key=parseVersion)

        for v in upgrade_versions:
            upgrade_files.append(os.path.join(root, f"{v}.sql"))

        return upgrade_files


def main():

    args = dict(
        database_login_user=dict(
            type='str'
        ),
        database_login_password=dict(
            type='str',
            no_log=True
        ),
        database_login_host=dict(
            type='str',
            default='localhost'
        ),
        database_login_port=dict(
            type='int',
            default=3306
        ),
        database_login_unix_socket=dict(
            type='str'
        ),
        database_config_file=dict(
            type='path'
        ),
        database_name=dict(
            required=True,
            type='str'
        ),
        icingadb_version=dict(
            required=True,
            type='str'
        ),
        icingadb_upgrade_directory=dict(
            required=True,
            type='str'
        ),
    )

    module = AnsibleModule(
        argument_spec=args,
        supports_check_mode=False,
    )

    icingadb = IcingaDbDatabaseUpdate(module)
    result = icingadb.run()

    module.log(msg=f"= result: {result}")

    module.exit_json(**result)


# import module snippets
if __name__ == '__main__':
    main()
