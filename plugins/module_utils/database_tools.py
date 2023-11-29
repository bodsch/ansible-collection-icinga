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

def db_connect(module, database_config_file, database_login_socket, database_login_host, database_login_port, database_login_user, database_login_password, database_name):
    """

    """
    config = {}

    config_file = database_config_file

    if config_file and os.path.exists(config_file):
        config['read_default_file'] = config_file

    if database_login_socket:
        config['unix_socket'] = database_login_socket
    else:
        config['host'] = database_login_host
        config['port'] = database_login_port

    # If login_user or login_password are given, they should override the
    # config file
    if database_login_user is not None:
        config['user'] = database_login_user
    if database_login_password is not None:
        config['passwd'] = database_login_password

    config['db'] = database_name

    try:
        db_connection = mysql_driver.connect(**config)

    except Exception as e:
        message = "unable to connect to database. "
        message += "check login_host, login_user and login_password are correct "
        message += f"or {config_file} has the credentials. "
        message += f"Exception message: {to_native(e)}"

        module.log(msg=message)

        return (None, None, True, message)

    return (db_connection.cursor(), db_connection, False, "successful connected")


def db_execute(module, db_cursor, db_connection, query, commit=True, rollback=True, close_cursor=False):
    """
    """
    state = False
    db_error = False
    db_message = None

    try:
        if not query.startswith("--"):
            db_cursor.execute(query)
            if commit:
                db_connection.commit()
        state = True

    except mysql_driver.Warning as e:
        try:
            error_id = e.args[0]
            error_msg = e.args[1]
            module.log(msg=f"WARNING: {error_id} - {error_msg}")
            pass
        except Exception:
            module.log(msg=f"WARNING: {str(e)}")
            pass

    except mysql_driver.Error as e:
        try:
            error_id = e.args[0]
            error_msg = e.args[1]

            if error_id == 1050:  # Table '...' already exists
                module.log(msg=f"WARNING: {error_msg}")
                pass
        except Exception:
            module.log(msg=f"ERROR: {str(e)}")
            pass

    except Exception as e:
        db_error = True
        db_message = f"Cannot execute SQL '{query}' : {to_native(e)}"

        if rollback:
            db_connection.rollback()

        pass

    finally:
        if close_cursor:
            db_cursor.close()

    return (state, db_error, db_message)


def db_import_sqlfile(module, sql_file, db_cursor, db_connection, commit=True, rollback=True, close_cursor=True):
    """
    """
    if not os.path.exists(sql_file):
        return (False, f"The file {sql_file} does not exist.")

    module.log(f"import sql file: {sql_file}")

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
                # module.log(f"execute statement: '{command}'")
                (state, db_error, db_message) = db_execute(module, db_cursor, db_connection, command, commit=False)
                if db_error:
                    break

        if rollback and db_error:
            db_connection.rollback()

        if commit and not db_error:
            db_connection.commit()

        if close_cursor and db_cursor:
            db_cursor.close()

    if db_error:
        state = True
        _msg = f"Cannot import file '{sql_file}' : {to_native(db_message)}"
    else:
        _msg = f"file '{sql_file}' successful imported."

    return (state, _msg)


def db_close_cursor(module, db_cursor):

    if db_cursor:
        db_cursor.close()


def check_table_schema(module, db_cursor, database_table_name):
    """
        :return:
            - state (bool)
            - db_error(bool)
            - db_error_message = (str|none)
    """
    q = f"SELECT * FROM information_schema.tables WHERE table_name = '{database_table_name}'"

    number_of_rows = 0

    try:
        number_of_rows = db_cursor.execute(q)
        db_cursor.fetchone()

    except Exception as e:
        module.fail_json(msg=f"Cannot execute SQL '{q}' : {to_native(e)}")
        pass

    finally:
        db_cursor.close()

    if number_of_rows == 1:
        return (True, False, "")

    return (False, False, "")


def current_version(module, db_cursor, database_table_name):
    """
    """
    _version = None
    _msg = None

    q = f"select version from {database_table_name} order by version desc limit 1"
    # q = f"select version from {database_table_name}"

    try:
        db_cursor.execute(q)
        _version = db_cursor.fetchone()[0]

    except Exception as e:
        _msg = f"Cannot execute SQL '{q}' : {to_native(e)}"
        pass

    finally:
        db_cursor.close()

    if _version:
        _msg = f"found version: {_version}"
        # module.log(_msg)

    return (_version, False, _msg)
