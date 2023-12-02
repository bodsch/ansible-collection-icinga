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

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: icingaweb_database_update.py
author:
    - 'Bodo Schulz'
short_description: handle database updates for icingaweb.
description: ''
"""

EXAMPLES = """
- name: update database version information
  become: true
  bodsch.icinga.icingaweb_database_update:
    database_login_host: database
    database_name: icingaweb_config
    database_config_file: /etc/icingaweb2/.my.cnf
    icingaweb_version: "2.11.3"
    icingaweb_upgrade_directory: "{{ icingaweb_upgrade_directory }}"
  register: _icingaweb_database_update
"""


class IcingaWeb2DatabaseUpdate(object):
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
        self.icingaweb_version = module.params.get("icingaweb_version")
        self.icingaweb_upgrade_directory = module.params.get("icingaweb_upgrade_directory")

        self.database_table_name = "icingaweb_dbversion"
        self.db_autocommit = True
        self.db_connect_timeout = 30

        self.state_directory = "/etc/icingaweb2/.ansible"

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

        # first step:
        # create table (if needed)
        (state, db_error, message) = self.__create_table_schema()

        if db_error:
            return dict(
                failed=True,
                msg=message
            )

        # step two:
        # check current version
        (current_version, db_error, message) = self.__current_version()

        if db_error:
            return dict(
                failed=True,
                msg=message
            )

        self.module.log(f"Database version: is {current_version} to should be {self.icingaweb_version}.")

        if not current_version:
            (state, db_error, message) = self.__update_version(version=self.icingaweb_version)

            if db_error:
                _failed = True
                _msg = message

            if state:
                _changed = True
                _msg = "version successful updated."
        else:
            # version compare
            if Version(current_version) == Version(self.icingaweb_version):
                # self.module.log("versions equal.")
                return dict(
                    changed=False,
                    failed=False,
                    msg="Icingaweb database is up to date."
                )

            elif Version(current_version) < Version(self.icingaweb_version):
                self.module.log(f"upgrade to version {self.icingaweb_version} needed.")
                (state, db_error, message) = self.upgrade_database(from_version=current_version)

                if db_error:
                    _failed = True

                if state:
                    _changed = True

                _msg = message

            else:
                return dict(
                    changed=False,
                    failed=False,
                    msg=f"icingaweb database downgrade are not supported. (current version are {current_version})"
                )

        return dict(
            changed=_changed,
            failed=_failed,
            msg=_msg
        )

    def __create_table_schema(self):
        """
            :return:
                - state (bool)
                - db_error(bool)
                - db_error_message = (str|none)
        """
        state = True
        db_error = False
        _msg = None

        (table_state, db_state, db_msg) = self.icinga_database.check_table_schema(self.database_table_name)

        if not table_state:
            q = f"""CREATE TABLE `{self.database_table_name}` (
              `dbversion_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
              `name` varchar(10) CHARACTER SET latin1 DEFAULT '',
              `version` varchar(10) CHARACTER SET latin1 DEFAULT '',
              `create_time` timestamp DEFAULT CURRENT_TIMESTAMP,
              `modify_time` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (`dbversion_id`),
              UNIQUE KEY `dbversion` (`name`)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8"""

            (state, db_error, db_message) = self.icinga_database.db_execute(q)

            if state:
                _msg = f"table {self.database_table_name} successful created."
            else:
                _msg = db_message

        return (state, db_error, _msg)

    def __update_version(self, version):
        """
        """
        q = f"""replace INTO {self.database_table_name} (name, version, modify_time)
            VALUES ('icingaweb', '{version}', now())"""

        (state, db_error, db_message) = self.icinga_database.db_execute(q)

        return (state, db_error, db_message)

    def upgrade_database(self, from_version="2.0.0"):
        """
        """
        state = False
        db_error = False
        db_message = None

        result_state = {}

        upgrade_files = self.__read_database_upgrades(from_version=from_version)

        db_error, db_message = self.icinga_database.db_connect()

        if db_error:
            return False, db_error, db_message

        for upgrade in upgrade_files:
            """
            """
            file_name = os.path.basename(upgrade)
            file_version = file_name.replace(".sql", "")

            result_state[str(file_version)] = {}

            self.module.log(msg=f"upgrade database to version: {file_version}")

            (state, _msg) = self.icinga_database.db_import_sqlfile(
                sql_file=file_name,
                commit=True,
                rollback=True,
                close_cursor=False
            )

            result_state[file_version].update({
                "failed": state,
                "msg": _msg
            })

            if not db_error:
                self.__update_version(file_version)
            else:
                break

        failed = (len({k: v for k, v in result_state.items() if v.get('failed', False)}) > 0)

        if failed:
            state = False

        return (state, db_error, result_state)

    def __read_database_upgrades(self, from_version="2.0.0"):
        """
        """
        _versions = []
        upgrade_files = []
        upgrade_versions = []

        self.module.log(msg=f"search versions between {from_version} and {self.icingaweb_version}")

        for root, dirs, files in os.walk(self.icingaweb_upgrade_directory, topdown=False):
            if files:
                _versions = files

        for v in _versions:
            """
            """
            version_string = v.replace(".sql", "")

            if version_string.startswith("2.0.0") or Version(version_string) <= Version(from_version):
                continue
            if Version(version_string) > Version(from_version) or Version(version_string) <= Version(self.icingaweb_version):
                upgrade_versions.append(version_string)

        # version sort
        upgrade_versions.sort(key=parseVersion)

        for v in upgrade_versions:
            self.module.log(msg=f"  - {v}")
            upgrade_files.append(os.path.join(root, f"{v}.sql"))

        return upgrade_files


# ===========================================
# Module execution.
#


def main():
    module = AnsibleModule(
        argument_spec=dict(
            database_login_user=dict(type='str'),
            database_login_password=dict(type='str', no_log=True),
            database_login_host=dict(type='str', default='localhost'),
            database_login_port=dict(type='int', default=3306),
            database_login_unix_socket=dict(type='str'),
            database_config_file=dict(type='path'),
            database_name=dict(required=True, type='str'),
            icingaweb_version=dict(required=True, type='str'),
            icingaweb_upgrade_directory=dict(required=True, type='str'),
        ),
        supports_check_mode=False,
    )

    icingaweb = IcingaWeb2DatabaseUpdate(module)
    result = icingaweb.run()

    module.log(msg="= result : '{}'".format(result))

    module.exit_json(**result)


# import module snippets
if __name__ == '__main__':
    main()
