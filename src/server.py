#!/opt/local/bin/python3
#
# robotframework-remoterunner-ssl: server
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

import logging
import re
import tempfile
import os
import sys
import logging
from robot.run import run
from socketserver import ThreadingMixIn, BaseServer
from xmlrpc.server import (
    SimpleXMLRPCServer,
    SimpleXMLRPCRequestHandler,
    SimpleXMLRPCDispatcher,
)
from xmlrpc.client import Binary
import socket
from OpenSSL import SSL
from base64 import b64decode
from threading import Thread, Condition
from _thread import start_new_thread
from pprint import pprint
import string
import traceback
import time
from http.server import BaseHTTPRequestHandler
from io import StringIO
from utils import (
    write_file_to_disk,
    read_file_from_disk,
    get_command_line_params_server,
    check_for_pip_package_condition,
)
import shutil
import subprocess
import importlib.util
import pkg_resources

# Set up the global logger variable
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(module)s -%(levelname)s- %(message)s"
)
logger = logging.getLogger(__name__)

# static stuff
DEFAULTKEYFILE = "privkey.pem"  # Replace with your PEM formatted key file
DEFAULTCERTFILE = "cacert.pem"  # Replace with your PEM formatted certificate file

DEFAULT_ADDRESS = "0.0.0.0"
DEFAULT_PORT = 1471


class RobotFrameworkServer:
    def test_connection(self):
        """
        Simple test method which returns an 'OK' string to the user
        Prior to calling this event, certificates and user/pass have
        already been validated

        Parameters
        ==========

        Returns
        =======
        msg: 'str'
            Fixed 'ok' response message
        """
        return "OK"

    def __init__(self, debug=False):
        """
        Constructor for RobotFrameworkServer

        Parameters
        ==========

        Returns
        =======
        debug: 'bool'
                Run in debug mode. This changes the logging level and does not cleanup the workspace
        """
        logger.setLevel(logging.DEBUG if debug else logging.INFO)

    @staticmethod
    def execute_robot_run(
        test_suites: dict,
        dependencies: dict,
        pip_dependencies: dict,
        client_enforces_server_package_upgrade: bool,
        robot_args: dict,
        debug=False,
    ):
        """
        Callback that is invoked when a request to execute a robot run is made

        Parameters
        ==========
        test_suites: 'dict'
            Dictionary of suites to execute
        dependencies: 'dict'
            Dictionary of files the test suites are dependent on
        pip_dependencies: 'list'
            List of pip packages that the user explicitly asked us to install
        client_enforces_server_package_upgrade: 'bool'
            Always upgrade pip packages on the server even if they are already installed. This is
            equivalent to the server's "upgrade-packages" option but allows you to control
            the upgrade through the client
        robot_args: 'dict'
            Dictionary of arguments to pass to robot.run()
        debug: 'bool'
            Run in debug mode. This changes the logging level and does not cleanup the workspace
        Returns
        =======
        test_results : 'dict'
            Dictionary containing test results and artifacts
        """
        workspace_dir = None
        std_out_err = None
        old_cwd = None
        try:
            old_log_level = logger.level
            if debug:
                logger.setLevel(logging.DEBUG)

            # Save all suites & dependencies to disk
            workspace_dir = RobotFrameworkServer._create_workspace(
                test_suites, dependencies
            )

            # Change the CWD to the workspace
            old_cwd = os.getcwd()
            os.chdir(workspace_dir)
            sys.path.append(workspace_dir)

            # Get the current value for our SSL environment variables (if configured)
            #
            # These variables might be set in case the user tests on localhost
            #
            # Prior to using pip, we need to unset these variables - otherwise,
            # pip will be unable to install the packages.
            #
            # Once the installation process has completed, we restore the original value(s)
            # whereas present.
            _SSL_CERT_FILE = os.getenv("SSL_CERT_FILE")
            _REQUESTS_CA_BUNDLE = os.getenv("REQUESTS_CA_BUNDLE")

            if _SSL_CERT_FILE:
                logger.debug(msg="Unsetting environment variable 'SSL_CERT_FILE'")
                os.unsetenv("SSL_CERT_FILE")
            if _REQUESTS_CA_BUNDLE:
                logger.debug(msg="Unsetting environment variable 'REQUESTS_CA_BUNDLE'")
                os.unsetenv("REQUESTS_CA_BUNDLE")

            # Check for external pip packages to be installed in case the
            # user has enabled pip decorators, but only if the server process
            # allows us to install them
            if len(pip_dependencies) > 0 and robot_upgrade_server_packages != "NEVER":
                logger.info(msg="Starting pip packages installation process ...")

                # get the installed pips
                installed_pips = {pkg.key for pkg in pkg_resources.working_set}
                pips_to_be_installed = []

                for pip_dependency in pip_dependencies.values():

                    # This is the pip package comparison operator
                    # which will tell our future package comparison
                    # about what comparison to use
                    # If the operator is not specicied, the package version will also
                    # not be specified, meaning that an 'equal' comparison on the
                    # latest package on PyPi wioll be performed if the server
                    # has been instructed to update the package via switch and decorator
                    pip_operator = None

                    # This is the placeholder for the pip version
                    # If the operator is not specicied, the package version was
                    # not be specified per regex, meaning that an 'equal' comparison on the
                    # latest package on PyPi wioll be performed if the server
                    # has been instructed to update the package via switch and decorator
                    pip_version = None

                    # Check if the user has provided the decorator with versioning information
                    # we already know at this point that we HAVE a decorator
                    mymatch = re.search(
                        pattern="(\S+)\s*(<=|<|>=|>)(\S+)", string=pip_dependency
                    )
                    if mymatch:
                        pip_package = mymatch[1]
                        pip_operator = mymatch[2]
                        pip_version = mymatch[3]
                    else:
                        # use the pip package 'as is', use the
                        # 'equal' operator and request "latest" package version
                        pip_package = pip_dependency
                        pip_operator = "=="
                        pip_version = "latest"

                    # Marker on whether we need to install this package or not
                    _install_the_package = False

                    # Start with the easy part - check if the package is not installed
                    if pip_package not in installed_pips:
                        # set a marker that we want to install this package
                        _install_the_package = True

                    # we know now that the package is installed
                    # Check if client process and/or server process always want us
                    # to apply an update, regardless
                    if (not _install_the_package) and (
                        robot_upgrade_server_packages == "ALWAYS"
                        or client_enforces_server_package_upgrade
                    ):
                        # set a marker that we want to install this package
                        _install_the_package = True

                    # Check if we are in upgrade-only mode
                    # Only upgrade the package if its version is not in scope of the
                    # given version specification (or 'latest' pip version)
                    if (
                        not _install_the_package
                        and robot_upgrade_server_packages == "OUTDATED"
                    ):
                        # The package is present in the list of our installed packages
                        # but we need to check its version
                        #
                        # Check if our version is installed AND fulfils the version requirements
                        # True = everything is ok
                        # False = installed but version does not suffice
                        # None = (probably) not installed yet - or other error
                        version_does_suffice = check_for_pip_package_condition(
                            package_name=pip_package,
                            compare_operator=pip_operator,
                            specific_version=pip_version,
                        )
                        # Either insufficient version or not installed
                        if not version_does_suffice:
                            _install_the_package = True

                    # Check if the package (excluding the version info!) is already installed
                    # If not, collect the entries with potential version info
                    # (but don't install the pip packages yet)
                    if _install_the_package:
                        if pip_dependency not in pips_to_be_installed:
                            pips_to_be_installed.append(pip_dependency)
                    else:
                        logger.debug(
                            msg=f"Skipping installation of pip package '{pip_dependency}'"
                        )

                if len(pips_to_be_installed) > 0:
                    logger.info(f"Pip package installation: startup...")

                    # Install all nonpresent pips. Note that this time, we honor
                    # potential versioning information that the user has specified
                    #
                    logger.info(
                        f"Pip package installation: installing: {','.join(pips_to_be_installed)}"
                    )

                    # prepare the installer string and start the installation
                    installer_exec = [sys.executable, "-m", "pip", "install"]
                    # activate upgrade mode in case the user has requested it
                    if robot_always_upgrade_packages:
                        installer_exec.append("--upgrade")
                    # These are the packages that we want/need to install
                    installer_exec.append(" ".join(pips_to_be_installed))

                    try:
                        subprocess.check_call(installer_exec)
                    except ex as Exception:
                        logger.info(
                            msg="Exception occurred while installing pip packages"
                        )
                        # restore the environment variables prior to raising the exception
                        if _SSL_CERT_FILE:
                            logger.debug(
                                msg="Restoring environment variable 'SSL_CERT_FILE'"
                            )
                            os.environ["SSL_CERT_FILE"] = _SSL_CERT_FILE
                        if _REQUESTS_CA_BUNDLE:
                            logger.debug(
                                msg="Restoring environment variable 'REQUESTS_CA_BUNDLE'"
                            )
                            os.environ["REQUESTS_CA_BUNDLE"] = _REQUESTS_CA_BUNDLE
                        raise

                    logger.info(f"Pip package installation: complete")

                logger.info(
                    msg="Successfully finished pip package installation process!"
                )

            # now restore our environment parameters whereas necessary
            if _SSL_CERT_FILE:
                logger.debug(msg="Restoring environment variable 'SSL_CERT_FILE'")
                os.environ["SSL_CERT_FILE"] = _SSL_CERT_FILE
            if _REQUESTS_CA_BUNDLE:
                logger.debug(msg="Restoring environment variable 'REQUESTS_CA_BUNDLE'")
                os.environ["REQUESTS_CA_BUNDLE"] = _REQUESTS_CA_BUNDLE

            # Execute the robot run
            std_out_err = StringIO()
            logger.debug(msg="Beginning Robot Run.")
            logger.debug(msg=f"Robot Run Args: {str(robot_args)}")
            ret_code = run(
                ".",
                stdout=std_out_err,
                stderr=std_out_err,
                outputdir=workspace_dir,
                name="Root",
                **robot_args,
            )
            logger.debug(msg="Robot Run finished")

            # Read the test artifacts from disk
            (
                output_xml,
                log_html,
                report_html,
            ) = RobotFrameworkServer._read_robot_artifacts_from_disk(workspace_dir)

            ret_val = {
                "std_out_err": Binary(std_out_err.getvalue().encode("utf-8")),
                "output_xml": Binary(output_xml.encode("utf-8")),
                "log_html": Binary(log_html.encode("utf-8")),
                "report_html": Binary(report_html.encode("utf-8")),
                "ret_code": ret_code,
            }
        except Exception as err:
            # Log here because the RPC framework doesn't give the client a full stacktrace
            logging.error(err)
            raise
        finally:
            if old_cwd:
                os.chdir(old_cwd)

            if std_out_err:
                std_out_err.close()

            if workspace_dir and not debug:
                shutil.rmtree(workspace_dir)

        logger.debug(msg="End of RPC function")
        # Revert the logger back to its original level
        logger.setLevel(old_log_level)
        return ret_val

    @staticmethod
    def _create_workspace(test_suites, dependencies):
        """
        Create a directory in the temporary directory and write all test suites & dependencies to disk

        Parameters
        ==========
        test_suites: 'dict'
            Dictionary of test suites
        dependencies: 'dict'
            Dictionary of files the test suites are dependent on

        Returns
        =======
        abspath : 'str'
            An absolute path to the directory created
        """
        workspace_dir = tempfile.mkdtemp()
        logger.debug(msg=f"Created workspace at: {workspace_dir}")

        for suite_name, suite in test_suites.items():
            full_dir = os.path.join(workspace_dir, suite.get("path"))
            if not os.path.exists(full_dir):
                os.makedirs(full_dir)
            full_path = os.path.join(full_dir, suite_name)
            logger.debug(msg=f"Writing suite to disk: {full_path}")
            write_file_to_disk(full_path, suite.get("suite_data"))

        for dep_name, dep_data in dependencies.items():
            full_path = os.path.join(workspace_dir, dep_name)
            logger.debug(msg=f"Writing dependency to disk: {full_path}")
            write_file_to_disk(full_path, dep_data)

        return workspace_dir

    @staticmethod
    def _read_robot_artifacts_from_disk(workspace_dir):
        """
        Read and return the contents of the output xml, log html and report html files generated by robot.

        Parameters
        ==========
        workspace_dir: 'str'
            Directory containing the test artifacts
        Returns
        =======
        File data (output xml, log html, report html) : 'tuple'
            Output files
        """

        log_html = ""
        log_html_path = os.path.join(workspace_dir, "log.html")
        if os.path.exists(log_html_path):
            logger.debug(msg=f"Reading log.html file off disk from: {log_html_path}")
            log_html = read_file_from_disk(log_html_path)

        report_html = ""
        report_html_path = os.path.join(workspace_dir, "report.html")
        if os.path.exists(report_html_path):
            logger.debug(
                msg=f"Reading report.html file off disk from: {report_html_path}"
            )
            report_html = read_file_from_disk(report_html_path)

        output_xml = ""
        output_xml_path = os.path.join(workspace_dir, "output.xml")
        if os.path.exists(output_xml_path):
            logger.debug(
                msg=f"Reading output.xml file off disk from: {output_xml_path}"
            )
            output_xml = read_file_from_disk(output_xml_path)

        return output_xml, log_html, report_html


class CustomThreadingMixIn:
    """Mix-in class to handle each request in a new thread."""

    # Decides how threads will act upon termination of the main process
    daemon_threads = True

    def process_request_thread(self, request, client_address):
        """Same as in BaseServer but as a thread.
        In addition, exception handling is done here.
        """
        try:
            self.finish_request(request, client_address)
            self.close_request(request)
        except (socket.error, SSL.SysCallError) as why:

            logger.info(
                msg=f"socket.error finishing request from {client_address}; Error: {why}"
            )
            self.close_request(request)
        except:
            self.handle_error(request, client_address)
            self.close_request(request)

    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        t = Thread(target=self.process_request_thread, args=(request, client_address))
        if self.daemon_threads:
            t.setDaemon(1)
        t.start()


class MyXMLRPCServer(CustomThreadingMixIn, SimpleXMLRPCServer):
    def __init__(
        self,
        ip,
        port,
        keyFile=DEFAULTKEYFILE,
        certFile=DEFAULTCERTFILE,
        logRequests=True,
    ):
        self.logRequests = logRequests

        class VerifyingRequestHandler(SimpleXMLRPCRequestHandler):
            def setup(myself):
                myself.connection = myself.request
                myself.rfile = socket.socket.makefile(
                    myself.request, "rb", myself.rbufsize
                )
                myself.wfile = socket.socket.makefile(
                    myself.request, "wb", myself.wbufsize
                )

            def address_string(myself):
                "getting 'FQDN' from host seems to stall on some ip addresses, so... just (quickly!) return raw host address"
                host, port = myself.client_address
                # return socket.getfqdn(host)
                return host

            def do_POST(myself):
                """Handles the HTTPS POST request.
                It was copied out from SimpleXMLRPCServer.py and modified to shutdown the socket cleanly.
                """
                try:
                    # get arguments
                    data = myself.rfile.read(int(myself.headers["content-length"]))
                    # In previous versions of SimpleXMLRPCServer, _dispatch
                    # could be overridden in this class, instead of in
                    # SimpleXMLRPCDispatcher. To maintain backwards compatibility,
                    # check to see if a subclass implements _dispatch and dispatch
                    # using that method if present.
                    response = myself.server._marshaled_dispatch(
                        data, getattr(myself, "_dispatch", None)
                    )
                except Exception as info:  # This should only happen if the module is buggy
                    logger.debug(msg=f"ERROR do_POST: {info}")
                    logger.debug(msg=f"Traceback follows: {traceback.print_exc()}")

                    # internal error, report as HTTP server error
                    myself.send_response(500)
                    myself.end_headers()
                else:
                    # got a valid XML RPC response
                    myself.send_response(200)
                    myself.send_header("Content-type", "text/xml")
                    myself.send_header("Content-length", str(len(response)))
                    myself.end_headers()
                    myself.wfile.write(response)

                    # shut down the connection
                    myself.wfile.flush()
                    myself.connection.shutdown()  # Modified here!

            def do_GET(myself):
                """Handles the HTTP GET request.

                Interpret all HTTP GET requests as requests for server
                documentation.
                """
                # Check that the path is legal
                if not myself.is_rpc_path_valid():
                    myself.report_404()
                    return

                response = myself.server.generate_html_documentation()
                myself.send_response(200)
                myself.send_header("Content-type", "text/html")
                myself.send_header("Content-length", str(len(response)))
                myself.end_headers()
                myself.wfile.write(response)

                # shut down the connection
                myself.wfile.flush()
                myself.connection.shutdown()  # Modified here!

            def report_404(myself):
                # Report a 404 error
                myself.send_response(404)
                response = "No such page"
                myself.send_header("Content-type", "text/plain")
                myself.send_header("Content-length", str(len(response)))
                myself.end_headers()
                myself.wfile.write(response)
                # shut down the connection
                myself.wfile.flush()
                myself.connection.shutdown()  # Modified here!

            def parse_request(myself):
                if SimpleXMLRPCRequestHandler.parse_request(myself):
                    basic, foo, encoded = myself.headers.get("Authorization").partition(
                        " "
                    )
                    username, foo, password = (
                        b64decode(encoded).decode("UTF-8").partition(":")
                    )
                    if username == robot_user and password == robot_pass:
                        return True
                    else:
                        myself.send_error(401, "Authentication failed")
                        return False

        SimpleXMLRPCDispatcher.__init__(self, False, None)
        BaseServer.__init__(self, (ip, port), VerifyingRequestHandler)

        # SSL socket stuff
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_privatekey_file(keyFile)
        ctx.use_certificate_file(certFile)

        self.socket = SSL.Connection(
            ctx, socket.socket(self.address_family, self.socket_type)
        )
        self.server_bind()
        self.server_activate()

        self.funcs = {}
        self.register_introspection_functions()
        self.register_instance(RobotFrameworkServer())

        # requests count and condition, to allow for keyboard quit via CTL-C
        self.requests = 0
        self.rCondition = Condition()

    def startup(self):
        # run until quit signaled from keyboard
        logger.info(
            msg="Robot Framework XMLRPC-SSL server startup complete; hit CTRL-C to quit..."
        )
        while True:
            try:
                self.rCondition.acquire()
                start_new_thread(
                    self.handle_request, ()
                )  # we do this async, because handle_request blocks!
                while not self.requests:
                    self.rCondition.wait(timeout=3.0)
                if self.requests:
                    self.requests -= 1
                self.rCondition.release()
            except KeyboardInterrupt:
                logger.info(msg="Shutting down ....")
                return

    def get_request(self):
        request, client_address = self.socket.accept()
        self.rCondition.acquire()
        self.requests += 1
        self.rCondition.notifyAll()
        self.rCondition.release()
        return (request, client_address)

    def listMethods(self):
        """return list of method names (strings)"""
        methodNames = self.funcs.keys()
        methodNames.sort()
        return methodNames

    def methodHelp(self, methodName):
        """method help"""
        if methodName in self.funcs:
            return self.funcs[methodName].__doc__
        else:
            raise Exception('method "%s" is not supported' % methodName)


if __name__ == "__main__":

    # Get our command line parameters
    (
        robot_log_level,
        robot_debug,
        robot_host,
        robot_port,
        robot_user,
        robot_pass,
        robot_keyfile,
        robot_certfile,
        robot_upgrade_server_packages,
    ) = get_command_line_params_server()

    logger.info(msg=f"robotframework-remoterunner-ssl: server init ....")

    # Check if the keyfile exists
    if not os.path.isfile(robot_keyfile):
        logger.info(msg=f"Keyfile '{robot_keyfile}' does not exist!")
        sys.exit(0)

    # Check if the certfile exists
    if not os.path.isfile(robot_certfile):
        logger.info(msg=f"Certfile '{robot_certfile}' does not exist!")

    # Server init
    server = MyXMLRPCServer(ip=robot_host, port=robot_port, logRequests=True)
    # Run the server's main loop
    sa = server.socket.getsockname()
    logger.info(
        msg=f"Securely serving remote Robot Framework requests on {sa[0]}:{sa[1]}"
    )

    # Server startup
    server.startup()
