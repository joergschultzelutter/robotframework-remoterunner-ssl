#!/opt/local/bin/python3
#
# robotframework-remoterunner-ssl: client
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
    get_command_line_params_client,
)
import sys
import shutil


# Set up the global logger variable
logger = logging.getLogger(__name__)

IMPORT_LINE_REGEX = re.compile("(Resource|Library)([\\s]+)([^[\\n\\r]*)([\\s]+)")


class RemoteFrameworkClient:
    def __init__(
        self,
        remote_connect_string: str,
        client_enforces_server_package_upgrade: bool,
        debug: bool = False,
    ):
        """
        Constructor for RemoteFrameworkClient

        Parameters
        ==========
        remote_connect_string : 'str'
            connect string, containing host, port, user and pass
        client_enforces_server_package_upgrade: 'bool'
            Always upgrade pip packages on the server even if they are already installed. This is
            exquivalent to the server's "always-upgrade-packages" option but allows you to control
            the upgrade through a client call
        debug: 'bool'
            run in debug mode. Enables extra logging and instructs the remote server not to cleanup the
            workspace after test execution

         Returns
         =======
        """

        self._debug = debug
        self._remote_connect_string = remote_connect_string
        self._client_enforces_server_package_upgrade = (
            client_enforces_server_package_upgrade
        )
        self._dependencies = {}
        self._pip_dependencies = {}
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

        Parameters
        ==========
        suite_list : 'list'
             List of paths to test suites or directories containing test suites
        extensions: 'str'
             String that filters the accepted file extensions for the test suites
        include_suites: 'dict'
            List of strings that filter suites to include
        robot_arg_dict: 'dict'
            Dictionary of arguments that will be passed to robot.run on the remote host

         Returns
         =======
        ResponseDict: 'dict'
            Dictionary containing stdout/err, log html, output xml, report html, return code
        """
        # Use robot to resolve all of the test suites
        suite_list = [os.path.normpath(p) for p in suite_list]
        logger.debug(msg=f"Suite List: {str(suite_list)}")

        # Let robot do the heavy lifting in parsing the test suites
        builder = self._create_test_suite_builder(include_suites, extensions)
        suite = builder.build(*suite_list)

        # Now iterate the suite's family tree, pull out the suites with test cases and resolve their dependencies.
        # Package them up into a dictionary that can be serialized
        self._package_suite_hierarchy(suite)

        # Make the RPC but do not disclose user/pw to the log file
        debug_connect_string = self._remote_connect_string.split("@")
        if len(debug_connect_string) > 0:
            debug_connect_string = debug_connect_string[len(debug_connect_string) - 1]
        logger.info(msg=f"Connecting to: {debug_connect_string}")

        p = ServerProxy(self._remote_connect_string)
        try:
            response = p.execute_robot_run(
                self._suites,
                self._dependencies,
                self._pip_dependencies,
                self._client_enforces_server_package_upgrade,
                robot_arg_dict,
                self._debug,
            )

        except ProtocolError as err:
            logger.info(msg=f"Error URL: {err.url}")
            logger.info(msg=f"Error code: {err.errcode}")
            logger.info(msg=f"Error message: {err.errmsg}")
            raise
        except ConnectionRefusedError as err:
            logger.info(msg=f"{debug_connect_string}: Connection refused!")
            raise
        except:
            raise

        return response

    @staticmethod
    def _create_test_suite_builder(include_suites, extensions):

        """
        Construct a robot.api.TestSuiteBuilder instance. There are argument name/type changes made at
        robotframework==3.2. This function attempts to initialize a TestSuiteBuilder instance assuming
        robotframework>=3.2, and falls back the the legacy arguments on exception.

        Parameters
        ==========
        include_suites : 'list'
                Suites to include
                string of extensions using a ':' as a join character
        Returns
        =======
        TestSuiteBuilder return value: 'robot.api.TestSuiteBuilder'

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

        Parameters
        ==========
        suite : 'robot.running.model.TestSuite'
                a TestSuite containing test cases
        Returns
        =======
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

        Parameters
        ==========
        suite : 'robot.running.model.TestSuite'
                a TestSuite containing test cases
        Returns
        =======
        file data / path : 'dict'
                Dictionary containing the suite file data and path from the root directory
        """
        logger.debug(f"Processing Test Suite: {suite.name}")
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

        Parameters
        ==========
        source : 'str'
                a Robot file or a path to a robot file
        Returns
        =======
        new_data_file : 'dict'
                Dictionary containing the suite file data and path from the root directory
        """

        # Check if we have to deal with a test file or e.g. a resource file
        if hasattr(source, "source"):
            file_path = source.source
            is_test_suite = True
        else:
            file_path = source
            is_test_suite = False

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
                pip_package = None

                # If filename (res_path) contains a comment, then separate
                # filename and comment
                if "#" in res_path:
                    _res_path_temp = res_path.split("#", 1)
                    res_path = _res_path_temp[0].strip()

                    # Now check the remainder (comment) for a pip decorator
                    _remainder = _res_path_temp[1].strip()
                    pipmatch = re.search(pattern="@pip:\s*(\S+)", string=_remainder)
                    if pipmatch:
                        pip_package = pipmatch[1]

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
                    # do we deal with a local library and not with
                    # something that we need to install from pypy?
                    # Find the actual file path
                    if not pip_package:
                        full_path = find_file(
                            res_path, os.path.dirname(file_path), imp_type
                        )

                    if imp_type == "Library":
                        # If user indicates that the library requires a pip package install,
                        # do not try to read the library from disk but rather add the pip package
                        # name to our pip package dependencies dictionary. Save both pip package name
                        # and external resource name - we need them both at a later point in time
                        if pip_package:
                            self._pip_dependencies[res_path] = pip_package
                        else:
                            # If its a Library (python file) then read the data and add to the dependencies
                            self._dependencies[filename] = read_file_from_disk(
                                full_path
                            )
                    else:
                        # If its a Resource, recurse down and parse it
                        self._process_robot_file(full_path)
            else:
                modified_file_lines.append(line)

        new_file_data = "".join(modified_file_lines)

        if not is_test_suite:
            self._dependencies[os.path.basename(file_path)] = new_file_data

        return new_file_data


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
        robot_client_enforces_server_package_upgrade,
    ) = get_command_line_params_client()

    logger.info(msg=f"robotframework-remoterunner-ssl: client init ....")

    # Set debug level
    level = logging.DEBUG if robot_debug else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s %(module)s -%(levelname)s- %(message)s"
    )

    # Create our future https connection string
    remote_connect_string = (
        f"https://{robot_user}:{robot_pass}@{robot_host}:{robot_port}"
    )

    # Check if user wants to execute plain connection test
    # If yes, connect to the server and execute the test method
    # Returns simple "ok" string if SSL connection was ok and
    # client user/pw matched server user/pw
    if robot_test_connection:
        p = ServerProxy(remote_connect_string)
        debug_connect_string = remote_connect_string.split("@")
        if len(debug_connect_string) > 0:
            debug_connect_string = debug_connect_string[len(debug_connect_string) - 1]
        logger.info(msg=f"Connecting to: {debug_connect_string}")
        try:
            logger.info(msg=p.test_connection())
        except ProtocolError as err:
            logger.info(msg=f"Error URL: {err.url}")
            logger.info(msg=f"Error code: {err.errcode}")
            logger.info(msg=f"Error message: {err.errmsg}")
        except ConnectionRefusedError as err:
            logger.info(msg=f"{debug_connect_string}: Connection refused!")
        except:
            raise
        sys.exit(0)

    # prepare the expected data types for the original robotframework-remoterunner core
    # convert input directory to list item if just one item was present
    if isinstance(robot_input_dir, str):
        robot_input_dir = [robot_input_dir]

    # Convert 'include' list items to colon-separated string, if necessary
    if isinstance(robot_include, list):
        robot_include = ":".join(robot_include)

    # Convert 'exclude' list items to colon-separated string, if necessary
    if isinstance(robot_exclude, list):
        robot_exclude = ":".join(robot_exclude)

    # Convert suites to List item if just one entry was present
    if isinstance(robot_suite, str):
        robot_suite = [robot_suite]

    # Convert 'test' list items to colon-separated string, if necessary
    if isinstance(robot_test, list):
        robot_test = ":".join(robot_test)

    # Convert 'exclude' list items to colon-separated string, if necessary
    if isinstance(robot_extension, list):
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
        remote_connect_string=remote_connect_string,
        client_enforces_server_package_upgrade=robot_client_enforces_server_package_upgrade,
        debug=robot_debug,
    )
    result = rfs.execute_run(
        suite_list=robot_input_dir,
        extensions=robot_extension,
        include_suites=robot_suite,
        robot_arg_dict=robot_args,
    )

    # In case the XMLRPC server did not return any content,
    # the 'result' value will be 'None'
    if result:
        # Print the robot stdout/stderr
        logger.info(msg="\nRobot execution response:")
        logger.info(msg=result.get("std_out_err"))

        output_dir = robot_output_dir
        if not os.path.exists(output_dir):
            logger.info(
                msg=f"Output directory {output_dir} does not exist; creating it for the user"
            )
            os.makedirs(output_dir)

        # Write the log html, report html, output xml
        if result.get("output_xml"):
            output_xml_path = resolve_output_path(
                filename=robot_output_file, output_dir=robot_output_dir
            )
            write_file_to_disk(
                output_xml_path, result["output_xml"].data.decode("utf-8")
            )
            logger.info(msg=f"Local Output:  {output_xml_path}")

        if result.get("log_html"):
            log_html_path = resolve_output_path(
                filename=robot_log_file, output_dir=robot_output_dir
            )
            write_file_to_disk(log_html_path, result["log_html"].data.decode("utf-8"))
            logger.info(f"Local Log:     {log_html_path}")

        if result.get("report_html"):
            report_html_path = resolve_output_path(
                filename=robot_report_file, output_dir=robot_output_dir
            )
            write_file_to_disk(
                report_html_path, result["report_html"].data.decode("utf-8")
            )
            logger.info(f"Local Report:  {report_html_path}")

        sys.exit(result.get("ret_code", 1))
    else:
        logger.info(msg="Did not receive data from repote XMLRPC server")
