from xmlrpc.client import ServerProxy
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

    user = "admin"
    pas = "admin"
    p = ServerProxy(f"https://{robot_user}:{robot_pass}@{robot_host}:{robot_port}")
    print(p.give_me_time())
