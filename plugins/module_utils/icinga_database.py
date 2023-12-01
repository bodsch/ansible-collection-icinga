#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# (c) 2023, Bodo Schulz <bodo@boone-schulz.de>
# Apache-2.0 (see LICENSE or https://opensource.org/license/apache-2-0)
# SPDX-License-Identifier: Apache-2.0

import os

from ansible.module_utils._text import to_native
from ansible.module_utils.mysql import (
    mysql_driver, mysql_driver_fail_msg
)


class IcingaDatabase():

    def __init__(self, module, hostname="localhost", port=3306, socket=None, config_file=None):
        """
        """
        self.module = module
        self.db_config = config_file
        self.db_socket = socket
        self.db_host = hostname
        self.db_port = port

    def db_connect(self, db_username, db_password, db_schema_name):
        """
            connect to Database
        """
        db_connection = None
        db_cursor = None
        db_connect_error = True

        config = {}

        if self.db_config and os.path.exists(self.db_config):
            config['read_default_file'] = self.db_config

        if self.db_socket:
            config['unix_socket'] = self.db_socket
        else:
            config['host'] = self.db_host
            config['port'] = self.db_port

        # If login_user or login_password are given, they should override the
        # config file
        if db_username is not None:
            config['user'] = db_username
        if db_password is not None:
            config['passwd'] = db_password

        config['db'] = db_schema_name

        try:
            db_connection = mysql_driver.connect(**config)
            db_cursor = db_connection.cursor()
            db_connect_error = False

        except Exception as e:
            message = "unable to connect to database. "
            message += "check login_host, login_user and login_password are correct "
            message += f"or {self.db_config} has the credentials. "
            message += f"Exception message: {to_native(e)}"

            self.module.log(msg=message)
            return (db_cursor, db_connection, db_connect_error, message)

        return (db_cursor, db_connection, db_connect_error, "successful connected")


    def db_execute(self, query, commit=True, rollback=True, close_cursor=False):
        """
            execute Query
        """
        state = False
        db_error = False
        db_message = None

        try:
            if not query.startswith("--"):
                self.db_cursor.execute(query)
                if commit:
                    self.db_connection.commit()
            state = True

        except mysql_driver.Warning as e:
            try:
                error_id = e.args[0]
                error_msg = e.args[1]
                self.module.log(msg=f"WARNING: {error_id} - {error_msg}")
                pass
            except Exception:
                self.module.log(msg=f"WARNING: {str(e)}")
                pass

        except mysql_driver.Error as e:
            try:
                error_id = e.args[0]
                error_msg = e.args[1]

                if error_id == 1050:  # Table '...' already exists
                    self.module.log(msg=f"WARNING: {error_msg}")
                    pass
            except Exception:
                self.module.log(msg=f"ERROR: {str(e)}")
                pass

        except Exception as e:
            db_error = True
            db_message = f"Cannot execute SQL '{query}' : {to_native(e)}"

            if rollback:
                self.db_connection.rollback()

            pass

        finally:
            if close_cursor:
                self.db_cursor.close()

        return (state, db_error, db_message)


    def db_import_sqlfile(self, sql_file, commit=True, rollback=True, close_cursor=True):
        """
            import complete SQL script
        """
        if not os.path.exists(sql_file):
            return (False, f"The file {sql_file} does not exist.")

        self.module.log(f"import sql file: {sql_file}")

        state = False
        db_error = False
        db_message = None
        _msg = None

        with open(sql_file, encoding='utf8') as f:
            sql_data = f.read()
            f.close()
            sql_commands = sql_data.split(';\n')
            # remove all lines with '--' prefix (SQL comments)
            # replace \n and strip lines
            sql_commands = [x.replace("\n","").strip() for x in sql_commands if not x.replace("\n","").strip().startswith("--")]

            for command in sql_commands:
                state = False
                db_error = False
                db_message = None

                if command:
                    # self.module.log(f"execute statement: '{command}'")
                    (state, db_error, db_message) = self.db_execute(command, commit=False)
                    if db_error:
                        break

            if rollback and db_error:
                self.db_connection.rollback()

            if commit and not db_error:
                self.db_connection.commit()

            if close_cursor and self.db_cursor:
                self.db_cursor.close()

        if db_error:
            state = True
            _msg = f"Cannot import file '{sql_file}' : {to_native(db_message)}"
        else:
            _msg = f"file '{sql_file}' successful imported."

        return (state, _msg)


    def check_table_schema(self, database_table_name):
        """
            :return:
                - state (bool)
                - db_error(bool)
                - db_error_message = (str|none)
        """
        q = f"SELECT * FROM information_schema.tables WHERE table_name = '{database_table_name}'"

        number_of_rows = 0

        try:
            number_of_rows = self.db_cursor.execute(q)
            self.db_cursor.fetchone()

        except Exception as e:
            self.module.fail_json(msg=f"Cannot execute SQL '{q}' : {to_native(e)}")
            pass

        finally:
            self.db_cursor.close()

        if number_of_rows == 1:
            return (True, False, "")

        return (False, False, "")


    def current_version(self, database_table_name):
        """
        """
        _version = None
        _msg = None

        q = f"select version from {database_table_name} order by version desc limit 1"
        # q = f"select version from {database_table_name}"

        try:
            self.db_cursor.execute(q)
            _version = self.db_cursor.fetchone()[0]

        except Exception as e:
            _msg = f"Cannot execute SQL '{q}' : {to_native(e)}"
            pass

        finally:
            self.db_cursor.close()

        if _version:
            _msg = f"found version: {_version}"
            # self.module.log(_msg)

        return (_version, False, _msg)
