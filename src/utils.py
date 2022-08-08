#!/opt/local/bin/python3
#
# robotframework-remoterunner-ssl: utility functions
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

from io import open
import os
import re
import argparse


PORT_INC_REGEX = ".*:[0-9]{1,5}$"


def read_file_from_disk(path, encoding="utf-8", into_lines=False):
    """
    Utility function to read and return a file from disk

    Parameters
    ==========
    path: 'str'
        Path to the file to read
    encoding: 'str'
        Encoding of the file
    into_lines: 'bool'
        Whether or not to return a list of lines

    Returns
    =======
    contents : 'str'
        Contents of the file
    """
    with open(path, "r", encoding=encoding) as file_handle:
        return file_handle.readlines() if into_lines else file_handle.read()


def write_file_to_disk(path, file_contents, encoding="utf-8"):
    """
     Utility function to write a file to disk

    Parameters
    ==========
    path: 'str'
        Path to write to
    file_contents: 'str'
        Contents of the file
    encoding: 'str'
        Encoding of the file

    Returns
    =======
    """
    with open(path, "w", encoding=encoding) as file_handle:
        file_handle.write(str(file_contents))


def calculate_ts_parent_path(suite):
    """
    Parses up a test suite's ancestry and builds up a file path. This will then be used to create the correct test
    suite hierarchy on the remote host

    Parameters
    ==========
    suite: 'robot.running.model.TestSuite'
        test suite to parse the ancestry for

    Returns
    =======
    file_path : 'str'
        file path of where the given suite is relative to the root test suite
    """
    family_tree = []

    if not suite.parent:
        return ""
    current_suite = suite.parent
    while current_suite:
        family_tree.append(current_suite.name)
        current_suite = current_suite.parent

    # Stick with unix style slashes for consistency
    return os.path.join(*reversed(family_tree)).replace("\\", "/")


def resolve_output_path(filename: str, output_dir: str):
    """
    Determine a path to output a file artifact based on whether the user specified the specific path

    Parameters
    ==========
    filename : 'str'
        Name of the file e.g. log.html
    output_dir: 'str'
        name / path of the future output directory

    Returns
    =======
    filename : 'str'
        Absolute path of where to save the test artifact
    """
    ret_val = filename

    if not os.path.isabs(filename):
        ret_val = os.path.abspath(os.path.join(output_dir, filename))

    return os.path.normpath(ret_val)


def get_command_line_params_server():
    """
    Function which gets the command line params from the user
    Parameters
    ==========
    Returns
    =======
    all parameters that the user has specified
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--host",
        dest="robot_host",
        default="localhost",
        type=str,
        help="Address to bind to. Default is 'localhost'",
    )

    parser.add_argument(
        "--port",
        dest="robot_port",
        default=8111,
        type=int,
        help="Port to listen on. Default is 8111",
    )

    parser.add_argument(
        "--user",
        dest="robot_user",
        default="admin",
        type=str,
        help="User name for BasicAuth authentification. Default value is 'admin'",
    )

    parser.add_argument(
        "--pass",
        dest="robot_pass",
        default="admin",
        type=str,
        help="password for BasicAuth authentification. Default value is 'admin'",
    )

    parser.add_argument(
        "--keyfile",
        dest="robot_keyfile",
        default="privkey.pem",
        type=str,
        help="SSL private key for secure communication. Default value is 'privkey.pem'",
    )

    parser.add_argument(
        "--certfile",
        dest="robot_certfile",
        default="cacert.pem",
        type=str,
        help="SSL certfile for secure communication. Default value is 'cacert.pem'",
    )

    parser.add_argument(
        "--log-level",
        choices={"TRACE", "DEBUG", "INFO", "WARN", "NONE"},
        default="WARN",
        type=str.upper,
        dest="robot_log_level",
        help="Robot Framework log level. Valid values = TRACE, DEBUG, INFO, WARN, NONE. Default value = WARN",
    )

    parser.add_argument(
        "--always-upgrade-packages",
        dest="robot_always_upgrade_packages",
        action="store_true",
        help="If your Robot Framework suite depends on external pip packages, always upgrade these packages"
        " on the XMLRPC server even if they are already installed. Similar to the client argument"
        " 'always-upgrade-server-packages' but forces the upgrade for each test (regardless of the client"
        " settings)."
    )

    parser.add_argument(
        "--debug",
        dest="robot_debug",
        action="store_true",
        help="Enables debug logging and will not delete the temporary directory after a robot run",
    )

    args = parser.parse_args()

    robot_log_level = args.robot_log_level
    robot_debug = args.robot_debug
    robot_host = args.robot_host
    robot_port = args.robot_port
    robot_user = args.robot_user
    robot_pass = args.robot_pass
    robot_keyfile = args.robot_keyfile
    robot_certfile = args.robot_certfile
    robot_always_upgrade_packages = args.robot_always_upgrade_packages

    return (
        robot_log_level,
        robot_debug,
        robot_host,
        robot_port,
        robot_user,
        robot_pass,
        robot_keyfile,
        robot_certfile,
        robot_always_upgrade_packages,
    )


def check_if_input_dir_exists(dir: str):
    """
    Helper method for parsing the command line params
    Parameters
    ==========
    dir : 'str'
            input directory
    Returns
    =======
    dir : 'str'
            input directory
    """

    if not os.path.isdir(dir):
        raise ValueError(f"Value '{dir}' is not a valid input directory")
    else:
        return dir


def get_command_line_params_client():
    """
    Function which gets the command line params from the user
    Parameters
    ==========
    Returns
    =======
    all parameters that the user has specified
    """
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--test-connection",
        dest="robot_test_connection",
        action="store_true",
        help="Enable this option to check if both client and server are properly configured. Returns a simple 'ok' "
        "string to the client if it was able to establish a secure connection to the remote XMLRPC server and "
        "supplied user/pass credentials were ok",
    )

    parser.add_argument(
        "--host",
        dest="robot_host",
        default="localhost",
        type=str,
        help="IP or Hostname of the server to execute the robot run on. Default value = localhost",
    )

    parser.add_argument(
        "--port",
        dest="robot_port",
        default=8111,
        type=int,
        help="Port number of the server to execute the robot run on. Default value = 8111",
    )

    parser.add_argument(
        "--user",
        dest="robot_user",
        default="admin",
        type=str,
        help="Server user name. Default value = admin",
    )

    parser.add_argument(
        "--pass",
        dest="robot_pass",
        default="admin",
        type=str,
        help="Server user passwort. Default value = admin",
    )

    parser.add_argument(
        "--log-level",
        choices={"TRACE", "DEBUG", "INFO", "WARN", "NONE"},
        default="WARN",
        type=str.upper,
        dest="robot_log_level",
        help="Threshold level for logging. Available levels: TRACE, DEBUG, INFO (default), WARN, NONE (no logging). "
        "Use syntax `LOGLEVEL:DEFAULT` to define the default visible log level in log files. Examples: "
        "--loglevel DEBUG --loglevel DEBUG:INFO",
    )

    parser.add_argument(
        "--suite",
        action="extend",
        nargs="+",
        dest="robot_suite",
        type=str,
        help="Select test suites to run by name. When this option is used with --test, --include or --exclude, "
        "only test cases in matching suites and also matching other filtering criteria are selected. Name can be "
        "a simple pattern similarly as with --test and it can contain parent name separated with a dot. You can "
        "specify this parameter multiple times, if necessary.",
    )

    parser.add_argument(
        "--test",
        action="extend",
        nargs="+",
        dest="robot_test",
        type=str,
        help="Select test cases to run by name or long name. Name is case insensitive and it can also be a simple "
        "pattern where `*` matches anything and `?` matches any char. You can specify this parameter multiple "
        "times, if necessary.",
    )

    parser.add_argument(
        "--include",
        action="extend",
        nargs="+",
        dest="robot_include",
        type=str,
        help="Select test cases to run by tag. Similarly as name with --test, tag is case and space insensitive and "
        "it is possible to use patterns with `*` and `?` as wildcards. Tags and patterns can also be combined "
        "together with `AND`, `OR`, and `NOT` operators. Examples: --include foo, --include bar*, "
        "--include fooANDbar*",
    )

    parser.add_argument(
        "--exclude",
        action="extend",
        nargs="+",
        dest="robot_exclude",
        type=str,
        help="Select test cases not to run by tag. These tests are not run even if included with --include. Tags are "
        "matched using the rules explained with --include.",
    )

    parser.add_argument(
        "--extension",
        action="extend",
        nargs="+",
        dest="robot_extension",
        type=str,
        help="Parse only files with this extension when executing a directory. Has no effect when running individual "
        "files or when using resource files. You can specify this parameter multiple times, if necessary. "
        "Specify the value without leading '.'. Example: `--extension robot`. Default extensions: robot, text, "
        "txt, resource",
    )

    parser.add_argument(
        "--output-dir",
        dest="robot_output_dir",
        type=str,
        default=".",
        help="Output directory which will host your output files. If a nonexisting dictionary is specified, "
        "it will be created for you. Default value: current directory",
    )

    parser.add_argument(
        "--input-dir",
        dest="robot_input_dir",
        action="extend",
        nargs="+",
        type=check_if_input_dir_exists,
        help="Input directory (containing your robot tests). You can specify this parameter multiple times, "
        "if necessary. Default value: current directory",
    )

    parser.add_argument(
        "--output-file",
        dest="robot_output_file",
        type=str,
        default="remote_output.xml",
        help="Robot Framework output file name. Default value: remote_output.xml",
    )

    parser.add_argument(
        "--log-file",
        dest="robot_log_file",
        type=str,
        default="remote_log.html",
        help="Robot Framework log file name. Default value: remote_log.html",
    )
    parser.add_argument(
        "--report-file",
        dest="robot_report_file",
        type=str,
        default="remote_report.html",
        help="Robot Framework report file name. Default value: remote_report.html",
    )

    parser.add_argument(
        "--always-upgrade-server-packages",
        dest="robot_always_upgrade_server_packages",
        action="store_true",
        help="If your Robot Framework suite depends on external pip packages, always upgrade these packages"
        " on the remote XMLRPC server even if they are already installed. This is the equivalent to the"
        " server's 'always-upgrade-packages' option which allows you to control a forced update through"
        " the client.",
    )

    parser.add_argument(
        "--debug",
        dest="robot_debug",
        action="store_true",
        help="Run in debug mode. This will enable debug logging and does not cleanup the workspace directory on the "
        "remote machine after test execution",
    )
    # run the parser
    args = parser.parse_args()

    # assign values to target variables and return
    # them back to the user
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
    robot_test_connection = args.robot_test_connection
    robot_output_dir = args.robot_output_dir
    robot_input_dir = args.robot_input_dir
    robot_extension = args.robot_extension
    robot_output_file = args.robot_output_file
    robot_log_file = args.robot_log_file
    robot_report_file = args.robot_report_file
    robot_always_upgrade_server_packages = args.robot_always_upgrade_server_packages

    # populate defaults in case the user has not specified a value
    # obviously, argparse's 'extend' option does not permit defaults
    robot_input_dir = "." if not robot_input_dir else robot_input_dir
    robot_extension = (
        ["robot", "txt", "text", "resource"] if not robot_extension else robot_extension
    )

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
        robot_test_connection,
        robot_output_dir,
        robot_input_dir,
        robot_extension,
        robot_output_file,
        robot_log_file,
        robot_report_file,
        robot_always_upgrade_server_packages,
    )


if __name__ == "__main__":
    pass
