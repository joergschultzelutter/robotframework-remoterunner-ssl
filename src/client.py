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
import re
import logging
from utils import (
    calculate_ts_parent_path,
    read_file_from_disk,
    resolve_output_path,
    write_file_to_disk,
)
import sys
import shutil


# Set up the global logger variable
logger = logging.getLogger(__name__)

IMPORT_LINE_REGEX = re.compile("(Resource|Library)([\\s]+)([^[\\n\\r]*)([\\s]+)")


class RemoteFrameworkClient:
    def __init__(self, remote_connect_string: str, debug=False):
        """
        Constructor for RemoteFrameworkClient

        :param address: Hostname/IP of the server with optional :Port
        :type address: str
        :param debug: Run in debug mode. Enables extra logging and instructs the remote server not to cleanup the
        workspace after test execution
        :type debug: bool
        """
        self._debug = debug
        self._remote_connect_string = remote_connect_string
        self._dependencies = {}
        self._suites = {}
        logger.setLevel(logging.DEBUG if debug else logging.INFO)

    def execute_run(
        self,
        suite_list: list,
        extensions: str,
        include_suites: list,
        robot_arg_dict: dict,
    ):
        """
        Sources a series of test suites and then makes the RPC call to the
        agent to execute the robot run.

        :param suite_list: List of paths to test suites or directories containing test suites
        :type suite_list: list
        :param extensions: String that filters the accepted file extensions for the test suites
        :type extensions: str
        :param include_suites: List of strings that filter suites to include
        :type include_suites: list
        :param robot_arg_dict: Dictionary of arguments that will be passed to robot.run on the remote host
        :type robot_arg_dict: dict

        :return: Dictionary containing stdout/err, log html, output xml, report html, return code
        :rtype: dict
        """
        # Use robot to resolve all of the test suites
        suite_list = [os.path.normpath(p) for p in suite_list]
        logger.debug("Suite List: %s", str(suite_list))

        # Let robot do the heavy lifting in parsing the test suites
        builder = self._create_test_suite_builder(include_suites, extensions)
        suite = builder.build(*suite_list)

        # Now iterate the suite's family tree, pull out the suites with test cases and resolve their dependencies.
        # Package them up into a dictionary that can be serialized
        self._package_suite_hierarchy(suite)

        # Make the RPC
        logger.info("Connecting to: %s", self._remote_connect_string)

        p = ServerProxy(self._remote_connect_string)
        try:
            response = p.execute_robot_run(
                self._suites, self._dependencies, robot_arg_dict, self._debug
            )

        except ProtocolError as err:
            print(f"Error URL: {err.url}")
            print(f"Error code: {err.errcode}")
            print(f"Error message: {err.errmsg}")
            response = None
        except ConnectionRefusedError as err:
            print("Connection refused!")
            response = None
        except:
            raise

        return response

    @staticmethod
    def _create_test_suite_builder(include_suites, extensions):
        """
        Construct a robot.api.TestSuiteBuilder instance. There are argument name/type changes made at
        robotframework==3.2. This function attempts to initialize a TestSuiteBuilder instance assuming
        robotframework>=3.2, and falls back the the legacy arguments on exception.

        :param include_suites: Suites to include
        :type include_suites: list
        :param extensions: string of extensions using a ':' as a join character

        :return: TestSuiteBuilder instance
        :rtype: robot.api.TestSuiteBuilder
        """
        if extensions:
            split_ext = list(ext.lower().lstrip(".") for ext in extensions.split(":"))
        else:
            split_ext = ["robot"]
        try:
            builder = TestSuiteBuilder(include_suites, included_extensions=split_ext)
        except TypeError:
            # Pre robotframework 3.2 API
            builder = TestSuiteBuilder(
                include_suites, extension=extensions
            )  # pylint: disable=unexpected-keyword-arg

        return builder

    def _package_suite_hierarchy(self, suite):
        """
        Parses through a Test Suite and its child Suites and packages them up into a dictionary so they can be
        serialized

        :param suite: robot test suite
        :type suite: TestSuite
        """
        # Empty suites in the hierarchy are likely directories so we're only interested in ones that contain tests
        if suite.tests:
            # Use the actual filename here rather than suite.name so that we preserve the file extension
            suite_filename = os.path.basename(suite.source)
            self._suites[suite_filename] = self._process_test_suite(suite)

        # Recurse down and process child suites
        for sub_suite in suite.suites:
            self._package_suite_hierarchy(sub_suite)

    def _process_test_suite(self, suite):
        """
        Processes a TestSuite containing test cases and performs the following:
            - Parses the suite's dependencies (e.g. Library & Resource references) and adds them into the `dependencies`
            dict
            - Corrects the path references in the suite file to where the dependencies will be placed on the remote side
            - Returns a dict with metadata alongside the updated test suite file data

        :param suite: a TestSuite containing test cases
        :type suite: robot.running.model.TestSuite

        :return: Dictionary containing the suite file data and path from the root directory
        :rtype: dict
        """
        logger.debug("Processing Test Suite: %s", suite.name)
        # Traverse the suite's ancestry to work out the directory path so that it can be recreated on the remote side
        path = calculate_ts_parent_path(suite)

        # Recursively parse and process all dependencies and return the patched test suite file
        updated_file = self._process_robot_file(suite)

        return {"path": path, "suite_data": updated_file}

    def _process_robot_file(self, source):
        """
        Processes a robot file (could be a Test Suite or a Resource) and performs the following:
            - Parses the files's robot dependencies (e.g. Library & Resource references) and adds them into the
            `dependencies` dict
            - Corrects the path references in the suite file to where the dependencies will be placed on the remote side
            - Returns the updated robot file data

        :param source: a Robot file or a path to a robot file
        :type source: robot.running.model.TestSuite | str

        :return: Dictionary containing the suite file data and path from the root directory
        :rtype: dict
        """
        file_path = source.source
        is_test_suite = True

        modified_file_lines = []
        # Read the actual file from disk
        file_lines = read_file_from_disk(file_path, into_lines=True)

        for line in file_lines:
            # Check if the current line is a Library or Resource import
            matches = IMPORT_LINE_REGEX.search(line)
            if matches and len(matches.groups()) == 4:
                imp_type = matches.group(1)
                whitespace_sep = matches.group(2)
                res_path = matches.group(3)
                # Replace the path with just the filename. They will be in the PYTHONPATH on the remote side so only
                # the filename is required.
                filename = os.path.basename(res_path)
                line_ending = matches.group(4)

                # Rebuild the updated line and append
                modified_file_lines.append(
                    imp_type + whitespace_sep + filename + line_ending
                )

                # If this not a dependency we've already dealt with and not a built-in robot library
                # (e.g. robot.libraries.Process)
                if (
                    filename not in self._dependencies
                    and not res_path.strip().startswith("robot.libraries")
                    and res_path.strip() not in STDLIBS
                ):
                    # Find the actual file path
                    full_path = find_file(
                        res_path, os.path.dirname(file_path), imp_type
                    )

                    if imp_type == "Library":
                        # If its a Library (python file) then read the data and add to the dependencies
                        self._dependencies[filename] = read_file_from_disk(full_path)
                    else:
                        # If its a Resource, recurse down and parse it
                        self._process_robot_file(full_path)
            else:
                modified_file_lines.append(line)

        new_file_data = "".join(modified_file_lines)

        if not is_test_suite:
            self._dependencies[os.path.basename(file_path)] = new_file_data

        return new_file_data


def check_if_input_dir_exists(dir: str):
    if not os.path.isdir(dir):
        raise ValueError(f"Value '{dir}' is not a valid input directory")
    else:
        return dir


def check_if_output_dir_exists(dir: str):
    if not os.path.isdir(dir):
        raise ValueError(f"Value '{dir}' is not a valid output directory")
    else:
        return dir


def get_command_line_params():
    parser = argparse.ArgumentParser()

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
        help="Threshold level for logging. Available levels: TRACE, DEBUG, INFO (default), WARN, NONE (no logging). Use syntax `LOGLEVEL:DEFAULT` to define the default visible log level in log files. Examples: --loglevel DEBUG --loglevel DEBUG:INFO",
    )

    parser.add_argument(
        "--suite",
        action="extend",
        nargs="+",
        dest="robot_suite",
        type=str,
        help="Select test suites to run by name. When this option is used with --test, --include or --exclude, only test cases in matching suites and also matching other filtering criteria are selected. Name can be a simple pattern similarly as with --test and it can contain parent name separated with a dot. You can specify this parameter multiple times, if necessary.",
    )

    parser.add_argument(
        "--test",
        action="extend",
        nargs="+",
        dest="robot_test",
        type=str,
        help="Select test cases to run by name or long name. Name is case insensitive and it can also be a simple pattern where `*` matches anything and `?` matches any char. You can specify this parameter multiple times, if necessary.",
    )

    parser.add_argument(
        "--include",
        action="extend",
        nargs="+",
        dest="robot_include",
        type=str,
        help="Select test cases to run by tag. Similarly as name with --test, tag is case and space insensitive and it is possible to use patterns with `*` and `?` as wildcards. Tags and patterns can also be combined together with `AND`, `OR`, and `NOT` operators. Examples: --include foo, --include bar*, --include fooANDbar*",
    )

    parser.add_argument(
        "--exclude",
        action="extend",
        nargs="+",
        dest="robot_exclude",
        type=str,
        help="Select test cases not to run by tag. These tests are not run even if included with --include. Tags are matched using the rules explained with --include.",
    )

    parser.add_argument(
        "--extension",
        action="extend",
        nargs="+",
        dest="robot_extension",
        type=str,
        default="robot:txt:resource",
        help="Parse only files with this extension when executing a directory. Has no effect when running individual files or when using resource files. You can specify this parameter multiple times, if necessary. Examples: `--extension robot`",
    )

    parser.add_argument(
        "--debug",
        dest="robot_debug",
        action="store_true",
        help="Run in debug mode. This will enable debug logging and does not cleanup the workspace directory on the remote machine after test execution",
    )

    parser.add_argument(
        "--test-connection",
        dest="robot_test_connection",
        action="store_true",
        help="Use this test option to check if both client and server are properly configured. Returns a simple 'ok' string if the client was able to establish a connection to the server and user/pass were ok",
    )

    parser.add_argument(
        "--output-dir",
        dest="robot_output_dir",
        type=check_if_output_dir_exists,
        default=".",
        help="Output directory which will host your output files. Default: current directory",
    )

    parser.add_argument(
        "--input-dir",
        dest="robot_input_dir",
        type=check_if_input_dir_exists,
        default=".",
        help="Input directory (containing your robot tests). Parameter can be specified multiple times",
    )

    parser.add_argument(
        "--output-file",
        dest="robot_output_file",
        type=str,
        default="remote_output.xml",
        help="Robot Framework output file name. Default name = remote_output.xml",
    )
    parser.add_argument(
        "--log-file",
        dest="robot_log_file",
        type=str,
        default="remote_log.html",
        help="Robot Framework log file name. Default name = remote_log.html",
    )
    parser.add_argument(
        "--report-file",
        dest="robot_report_file",
        type=str,
        default="remote_report.html",
        help="Robot Framework report file name. Default name = remote_report.html",
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
    robot_test_connection = args.robot_test_connection
    robot_output_dir = args.robot_output_dir
    robot_input_dir = args.robot_input_dir
    robot_extension = args.robot_extension
    robot_output_file = args.robot_output_file
    robot_log_file = args.robot_log_file
    robot_report_file = args.robot_report_file

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
    )


if __name__ == "__main__":

    # Get the input parameters. We use a different parser than the
    # original robotframework-remoterunner. Our args parser mimicks the
    # original parser's behavior, meaning that e.g. if the user has
    # specified multiple include tags, our parameter's value will
    # be a colon-separated string and no longer a list item
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
        robot_test_connection,
        robot_output_dir,
        robot_input_dir,
        robot_extension,
        robot_output_file,
        robot_log_file,
        robot_report_file,
    ) = get_command_line_params()

    # Set debug level
    level = logging.DEBUG if robot_debug else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s %(module)s -%(levelname)s- %(message)s"
    )

    # Create the https connection string
    remote_connect_string = (
        f"https://{robot_user}:{robot_pass}@{robot_host}:{robot_port}"
    )

    # Check if user wants to execute plain connection test
    # If yes, connect to the server and execute the test method
    # Returns simple "ok" string if SSL connection was ok and
    # client user/pw matched server user/pw
    if robot_test_connection:
        p = ServerProxy(remote_connect_string)
        try:
            print(p.test_connection())
        except ProtocolError as err:
            print(f"Error URL: {err.url}")
            print(f"Error code: {err.errcode}")
            print(f"Error message: {err.errmsg}")
        except ConnectionRefusedError as err:
            print("Connection refused!")
        except:
            raise
        sys.exit(0)

    # prepare the expected data types for the original robotframework-remoterunner core
    # convert input directory to list item if just one item was present
    if isinstance(robot_input_dir, str):
        robot_input_dir = [robot_input_dir]

    # Convert 'include' list items to colon-separated string, if necessary
    if robot_include and isinstance(robot_include, list):
        robot_include = ":".join(robot_include)

    # Convert 'exclude' list items to colon-separated string, if necessary
    if robot_exclude and isinstance(robot_exclude, list):
        robot_exclude = ":".join(robot_exclude)

    # Convert suites to List item if just one entry was present
    if isinstance(robot_suite, str):
        robot_suite = [robot_suite]

    # Convert 'test' list items to colon-separated string, if necessary
    if robot_test and isinstance(robot_test, list):
        robot_test = ":".join(robot_test)

    # Convert 'exclude' list items to colon-separated string, if necessary
    if robot_extension and isinstance(robot_extension, list):
        robot_extension = ":".join(robot_extension)

    # Create the robot args parameter directory and add the
    # parameters whereas  present
    robot_args = {}

    # Add the parameters whereas present
    if robot_log_level:
        robot_args["loglevel"] = robot_log_level
    if robot_include:
        robot_args["include"] = robot_include
    if robot_exclude:
        robot_args["exclude"] = robot_exclude
    if robot_test:
        robot_args["test"] = robot_test
    if robot_suite:
        robot_args["suite"] = robot_suite
    if robot_suite:
        robot_args["extension"] = robot_extension

    # Default branch for executing actual tests
    rfs = RemoteFrameworkClient(
        remote_connect_string=remote_connect_string, debug=robot_debug
    )
    result = rfs.execute_run(
        suite_list=robot_input_dir,
        extensions=robot_extension,
        include_suites=robot_suite,
        robot_arg_dict=robot_args,
    )
    # Print the robot stdout/stderr
    logger.info("\nRobot execution response:")
    logger.info(result.get("std_out_err"))

    output_dir = robot_output_dir
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Write the log html, report html, output xml
    if result.get("output_xml"):
        output_xml_path = resolve_output_path(
            filename=robot_output_file, output_dir=robot_output_dir
        )
        write_file_to_disk(output_xml_path, result["output_xml"].data.decode("utf-8"))
        logger.info("Local Output:  %s", output_xml_path)

    if result.get("log_html"):
        log_html_path = resolve_output_path(
            filename=robot_log_file, output_dir=robot_output_dir
        )
        write_file_to_disk(log_html_path, result["log_html"].data.decode("utf-8"))
        logger.info("Local Log:     %s", log_html_path)

    if result.get("report_html"):
        report_html_path = resolve_output_path(
            filename=robot_report_file, output_dir=robot_output_dir
        )
        write_file_to_disk(report_html_path, result["report_html"].data.decode("utf-8"))
        logger.info("Local Report:  %s", report_html_path)

    sys.exit(result.get("ret_code", 1))
