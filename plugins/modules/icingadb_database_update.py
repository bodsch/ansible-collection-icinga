#!/usr/bin/env python3

# -*- coding: utf-8 -*-

# (c) 2020, Bodo Schulz <bodo@boone-schulz.de>
# BSD 2-clause (see LICENSE or https://opensource.org/licenses/BSD-2-Clause)

from __future__ import absolute_import, print_function
import os
import sys
import warnings
import re

from enum import Enum

from packaging.version import Version, parse as parseVersion
from packaging.version import InvalidVersion

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six.moves import configparser
from ansible.module_utils._text import to_native
from ansible.module_utils.mysql import (
    mysql_driver, mysql_driver_fail_msg
)

from ansible_collections.bodsch.icinga.plugins.module_utils.database_tools import (
    db_connect, db_execute, db_import_sqlfile, db_close_cursor, check_table_schema, current_version
)

__metaclass__ = type

ANSIBLE_METADATA = {
    'metadata_version': '0.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = """
---
module: icingadb_database_update.py
author:
    - 'Bodo Schulz'
short_description: handle user and they preferences in a mysql.
description: ''
"""

EXAMPLES = """
- name: import icingaweb users into database
  become: true
  icingadb_database_update:
    database_login_host: database
    database_name: icingadb_config
    database_config_file: /etc/icingadb/.my.cnf
    icingadb_version: "2.11.3"
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

        if mysql_driver is None:
            self.module.fail_json(msg=mysql_driver_fail_msg)
        else:
            warnings.filterwarnings('error', category=mysql_driver.Warning)

        cursor, conn, db_error, db_message = db_connect(
            self.module,
            self.database_config_file,
            self.database_login_socket,
            self.database_login_host,
            self.database_login_port,
            self.database_login_user,
            self.database_login_password,
            self.database_name) # self.__mysql_connect()

        if db_error:
            return dict(
                failed = True,
                msg = db_message, # db_message
            )
            #return False, db_error, db_message

        # first step:
        # create table (if needed)
        # (state, db_error, message) = self.__create_table_schema()
        #
        # if db_error:
        #     return dict(
        #         failed=True,
        #         msg=message
        #     )

        # step two:
        # check current version
        (curr_version, db_error, message) = current_version(self.module, cursor, self.database_table_name)

        if db_error:
            return dict(
                failed=True,
                msg=message
            )

        # self.module.log(f" -> {curr_version} {db_error}, {message}")

        curr_version = self.version_string(curr_version)

        _msg = f"  versions: {curr_version} vs. {self.icingadb_version}"
        self.module.log(_msg)

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
                    changed = False,
                    failed = False,
                    msg = "icingaweb database is up to date."
                )

            elif Version(curr_version) < Version(self.icingadb_version):
                self.module.log(f"upgrade to version {self.icingadb_version} needed.")
                (state, db_error, message) = self.upgrade_database(from_version=curr_version)

                # self.module.log(msg=f" - upgrade_database  : {state}, {db_error}, {message}")

                if db_error:
                    _failed = True

                if state:
                    _changed = True

                _msg = message

            else:
                return dict(
                    changed = False,
                    failed = False,
                    msg = f"icingaweb database downgrade are not supported. (current version are {curr_version})"
                )

        return dict(
            changed = _changed,
            failed = _failed,
            msg = _msg
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


    # def __hash(self, plaintext):
    #     """
    #       https://docs.python.org/3/library/crypt.html
    #     """
    #     import crypt
    #     salt = ""
    #     try:
    #         salt = crypt.mksalt(crypt.METHOD_SHA512)
    #     except Exception:
    #         import random
    #         CHARACTERS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    #         salt = ''.join(random.choice(CHARACTERS) for i in range(16))
    #         # Use SHA512
    #         # return '$6$' + salt
    #
    #     return crypt.crypt(
    #         plaintext,
    #         salt
    #     )

    def __checksum(self, plaintext):
        """
        """
        import hashlib
        _bytes = plaintext.encode('utf-8')
        _hash = hashlib.sha256(_bytes)
        return _hash.hexdigest()

    # def __update_version(self, version):
    #     """
    #     """
    #     cursor, conn, db_error, db_message = self.__mysql_connect()
    #
    #     if db_error:
    #         return False, db_error, db_message
    #
    #     q = f"""replace INTO {self.database_table_name} (version)
    #         VALUES ('{version}')"""
    #
    #     state = False
    #     db_error = False
    #     db_message = None
    #
    #     try:
    #         cursor.execute(q)
    #         conn.commit()
    #         state = True
    #     except Exception as e:
    #         conn.rollback()
    #         state = False
    #         db_error = True
    #         db_message = f"Cannot execute SQL '{q}' : {to_native(e)}"
    #
    #         self.module.log(msg=db_message)
    #     finally:
    #         cursor.close()
    #
    #     return (state, db_error, db_message)

    def upgrade_database(self, from_version="1.0.0"):
        """
        """
        state = False
        db_error = False
        db_message = None

        result_state = {}

        upgrade_files = self.__read_database_upgrades(from_version=from_version)

        cursor, conn, db_error, db_message = db_connect(
            self.module,
            self.database_config_file,
            self.database_login_socket,
            self.database_login_host,
            self.database_login_port,
            self.database_login_user,
            self.database_login_password,
            self.database_name) # self.__mysql_connect()

        if db_error:
            return False, db_error, db_message

        for upgrade in upgrade_files:
            """
            """
            file_name = os.path.basename(upgrade)
            file_version = file_name.replace(".sql", "")

            result_state[str(file_version)] = {}

            # self.module.log(msg=f"upgrade database to version: {file_version}")

            sql_commands = []

            state = False
            db_error = False
            db_message = None
            _msg = None # f"file '{upgrade}' successful imported."

            state, msg = db_import_sqlfile(
                module=self.module,
                sql_file=upgrade,
                db_cursor=cursor,
                db_connection=conn,
                close_cursor=False
            )

            result_state[file_version].update({
                "failed": state,
                "msg": msg
            })

            if state:
                break

        if cursor:
            db_close_cursor(self.module, cursor)

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

        # self.module.log(msg=f"search versions between {from_version} and {self.icingadb_version}")

        for root, dirs, files in os.walk(self.icingadb_upgrade_directory, topdown=False):
            # self.module.log(msg=f"  - root : {root}")
            # self.module.log(msg=f"  - dirs : {dirs}")
            # self.module.log(msg=f"  - files: {files}")

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
        upgrade_versions.sort(key = parseVersion)

        for v in upgrade_versions:
            # self.module.log(msg=f"  - {v}")
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
            icingadb_version=dict(required=True, type='str'),
            icingadb_upgrade_directory=dict(required=True, type='str'),
        ),
        supports_check_mode=False,
    )

    icingaweb = IcingaDbDatabaseUpdate(module)
    result = icingaweb.run()

    module.log(msg="= result : '{}'".format(result))

    module.exit_json(**result)


# import module snippets
if __name__ == '__main__':
    main()
