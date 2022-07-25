import logging
import argparse
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

######
import ssl
######

# Set up the global logger variable
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(module)s -%(levelname)s- %(message)s"
)
logger = logging.getLogger(__name__)

# static stuff
DEFAULTKEYFILE = "privkey.pem"  # Replace with your PEM formatted key file
DEFAULTCERTFILE = "cacert.pem"  # Replace with your PEM formatted certificate file


class Services:
    def give_me_time(self):
        return time.asctime()


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

            print(
                'socket.error finishing request from "%s"; Error: %s'
                % (client_address, str(why))
            )

            self.close_request(request)
        except:
            self.handle_error(request, client_address)
            self.close_request(request)

    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        t = Thread(target=self.process_request_thread, args=(request, client_address))
        if self.daemon_threads:
            t.daemon = True
#            t.setDaemon(1)
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
                    print("ERROR do_POST: ", info)
                    print("Traceback follows:", traceback.print_exc())

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
                    if username == "admin":
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
        #######
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_OPTIONAL
        ########

        self.server_bind()
        self.server_activate()

        self.funcs = {}
        self.register_introspection_functions()
        self.register_instance(Services())

        # requests count and condition, to allow for keyboard quit via CTL-C
        self.requests = 0
        self.rCondition = Condition()

    def startup(self):
        # run until quit signaled from keyboard
        print("server starting; hit CTRL-C to quit...")
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
                print("quit signaled, i'm done.")
                return

    def get_request(self):
        request, client_address = self.socket.accept()
        self.rCondition.acquire()
        self.requests += 1
        self.rCondition.notify_all()
#        self.rCondition.notifyAll()
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
    server = MyXMLRPCServer(ip=robot_host, port=robot_port, logRequests=True)
    # Run the server's main loop
    sa = server.socket.getsockname()
    print("Serving HTTPS on", sa[0], "port", sa[1])

    server.startup()
