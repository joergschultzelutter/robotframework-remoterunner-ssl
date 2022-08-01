#!/opt/local/bin/python3
#
# robotframework-remoterunner-mt: client
# Author: Joerg Schultze-Lutter, 2021
#
# Parts of this software are based on the following open source projects:
#
# robotframework-remoterunner (https://github.com/chrisBrookes93/robotframework-remoterunner)
# python3-xmlrpc-ssl-basic-auth (https://github.com/etopian/python3-xmlrpc-ssl-basic-auth)
#
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
from xmlrpc.client import ServerProxy, ProtocolError
import argparse
from robot.api import TestSuiteBuilder
from robot.libraries import STDLIBS
from robot.utils.robotpath import find_file
import os
import logging
from utils import (
    normalize_xmlrpc_address,
    calculate_ts_parent_path,
    read_file_from_disk,
)

# Set up the global logger variable
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(module)s -%(levelname)s- %(message)s"
)
logger = logging.getLogger(__name__)


def get_command_line_params():
    parser = argparse.ArgumentParser()

    parser.add_argument("--host", dest="robot_host", default="localhost", type=str)

    parser.add_argument("--port", dest="robot_port", default=8111, type=int)

    parser.add_argument("--user", dest="robot_user", default="admin", type=str)

    parser.add_argument("--pass", dest="robot_pass", default="admin", type=str)

    parser.add_argument(
        "--keyfile", dest="robot_keyfile", default="privkey.pem", type=str
    )

    parser.add_argument(
        "--certfile", dest="robot_certfile", default="cacert.pem", type=str
    )

    parser.add_argument(
        "--log-level",
        choices={"TRACE", "DEBUG", "INFO", "WARN", "NONE"},
        default="WARN",
        type=str.upper,
        dest="robot_log_level",
        help="",
    )

    parser.add_argument(
        "--suite", action="extend", nargs="+", dest="robot_suite", type=str
    )

    parser.add_argument(
        "--test", action="extend", nargs="+", dest="robot_test", type=str
    )

    parser.add_argument(
        "--include", action="extend", nargs="+", dest="robot_include", type=str
    )

    parser.add_argument(
        "--exclude", action="extend", nargs="+", dest="robot_exclude", type=str
    )

    parser.add_argument(
        "--debug",
        dest="robot_debug",
        action="store_true",
        help="Enable debug mode",
    )

    parser.add_argument(
        "--test-connection",
        dest="robot_test_connection",
        action="store_true",
        help="Returns simple 'ok' string if a connection to the server could be established and user/pass are ok",
    )
    args = parser.parse_args()

    robot_log_level = args.robot_log_level
    robot_suite = args.robot_suite
    robot_test = args.robot_test
    robot_include = args.robot_include
    robot_exclude = args.robot_exclude
    robot_debug = args.robot_debug
    robot_host = args.robot_host
    robot_port = args.robot_port
    robot_user = args.robot_user
    robot_pass = args.robot_pass
    robot_keyfile = args.robot_keyfile
    robot_certfile = args.robot_certfile
    robot_test_connection = args.robot_test_connection

    return (
        robot_log_level,
        robot_suite,
        robot_test,
        robot_include,
        robot_exclude,
        robot_debug,
        robot_host,
        robot_port,
        robot_user,
        robot_pass,
        robot_keyfile,
        robot_certfile,
    )


if __name__ == "__main__":
    (
        robot_log_level,
        robot_suite,
        robot_test,
        robot_include,
        robot_exclude,
        robot_debug,
        robot_host,
        robot_port,
        robot_user,
        robot_pass,
        robot_keyfile,
        robot_certfile,
    ) = get_command_line_params()

    p = ServerProxy(f"https://{robot_user}:{robot_pass}@{robot_host}:{robot_port}")
    try:
        print(p.test_connection())
    except ProtocolError as err:
        print (f"Error code: {err.errcode}")
        print (f"Error message: {err.errmsg}")
