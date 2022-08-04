# robotframework-remoterunner-mt

This is a Python3 port of [chrisBrookes93](https://github.com/chrisBrookes93)'s [robotframework-remoterunner](https://github.com/chrisBrookes93/robotframework-remoterunner) to  [Etopian](https://github.com/etopian/)'s [https XMLRPC server](https://github.com/etopian/python3-xmlrpc-ssl-basic-auth), providing a remote multithreaded XMLRPC SSL server with BasicAuth support to Robot Framework users.

## Repo contents

The ```src``` directory from this repo contains two scripts:

- ```server.py``` - The server that receives and executes the robot run
- ```client.py``` - The client that invokes the server to execute the robot run on a remote machine

### client.py

```text
usage: client.py [-h] [--host ROBOT_HOST] [--port ROBOT_PORT] [--user ROBOT_USER] [--pass ROBOT_PASS] [--log-level {WARN,NONE,TRACE,DEBUG,INFO}] [--suite ROBOT_SUITE [ROBOT_SUITE ...]]
                 [--test ROBOT_TEST [ROBOT_TEST ...]] [--include ROBOT_INCLUDE [ROBOT_INCLUDE ...]] [--exclude ROBOT_EXCLUDE [ROBOT_EXCLUDE ...]]
                 [--extension ROBOT_EXTENSION [ROBOT_EXTENSION ...]] [--debug] [--test-connection] [--output-dir ROBOT_OUTPUT_DIR] [--input-dir ROBOT_INPUT_DIR [ROBOT_INPUT_DIR ...]]
                 [--output-file ROBOT_OUTPUT_FILE] [--log-file ROBOT_LOG_FILE] [--report-file ROBOT_REPORT_FILE]

optional arguments:
  -h, --help            show this help message and exit
  --host ROBOT_HOST     IP or Hostname of the server to execute the robot run on. Default value = localhost
  --port ROBOT_PORT     Port number of the server to execute the robot run on. Default value = 8111
  --user ROBOT_USER     Server user name. Default value = admin
  --pass ROBOT_PASS     Server user passwort. Default value = admin
  --log-level {WARN,NONE,TRACE,DEBUG,INFO}
                        Threshold level for logging. Available levels: TRACE, DEBUG, INFO (default), WARN, NONE (no logging). Use syntax `LOGLEVEL:DEFAULT` to define the default visible
                        log level in log files. Examples: --loglevel DEBUG --loglevel DEBUG:INFO
  --suite ROBOT_SUITE [ROBOT_SUITE ...]
                        Select test suites to run by name. When this option is used with --test, --include or --exclude, only test cases in matching suites and also matching other
                        filtering criteria are selected. Name can be a simple pattern similarly as with --test and it can contain parent name separated with a dot. You can specify this
                        parameter multiple times, if necessary.
  --test ROBOT_TEST [ROBOT_TEST ...]
                        Select test cases to run by name or long name. Name is case insensitive and it can also be a simple pattern where `*` matches anything and `?` matches any char.
                        You can specify this parameter multiple times, if necessary.
  --include ROBOT_INCLUDE [ROBOT_INCLUDE ...]
                        Select test cases to run by tag. Similarly as name with --test, tag is case and space insensitive and it is possible to use patterns with `*` and `?` as wildcards.
                        Tags and patterns can also be combined together with `AND`, `OR`, and `NOT` operators. Examples: --include foo, --include bar*, --include fooANDbar*
  --exclude ROBOT_EXCLUDE [ROBOT_EXCLUDE ...]
                        Select test cases not to run by tag. These tests are not run even if included with --include. Tags are matched using the rules explained with --include.
  --extension ROBOT_EXTENSION [ROBOT_EXTENSION ...]
                        Parse only files with this extension when executing a directory. Has no effect when running individual files or when using resource files. You can specify this
                        parameter multiple times, if necessary. Specify the value without leading '.'. Example: `--extension robot`. Default extensions: robot, text, txt, resource
  --debug               Run in debug mode. This will enable debug logging and does not cleanup the workspace directory on the remote machine after test execution
  --test-connection     Use this test option to check if both client and server are properly configured. Returns a simple 'ok' string if the client was able to establish a connection to
                        the server and user/pass were ok
  --output-dir ROBOT_OUTPUT_DIR
                        Output directory which will host your output files. If a nonexisting dictionary is specified, it will be created for you. Default: current directory
  --input-dir ROBOT_INPUT_DIR [ROBOT_INPUT_DIR ...]
                        Input directory (containing your robot tests). You can specify this parameter multiple times, if necessary. Default: current directory
  --output-file ROBOT_OUTPUT_FILE
                        Robot Framework output file name. Default name = remote_output.xml
  --log-file ROBOT_LOG_FILE
                        Robot Framework log file name. Default name = remote_log.html
  --report-file ROBOT_REPORT_FILE
                        Robot Framework report file name. Default name = remote_report.html
```

If no parameters are specified, the ```client.py``` script will connect to a server on ```localhost``` port ```8111``` while serving all robot files from the current directory

### server.py

```text
usage: server.py [-h] [--host ROBOT_HOST] [--port ROBOT_PORT] [--user ROBOT_USER] [--pass ROBOT_PASS] [--keyfile ROBOT_KEYFILE] [--certfile ROBOT_CERTFILE]
                 [--log-level {TRACE,NONE,DEBUG,INFO,WARN}] [--debug]

optional arguments:
  -h, --help            show this help message and exit
  --host ROBOT_HOST     Address to bind to. Default is 'localhost'
  --port ROBOT_PORT     Port to listen on. Default is 8111
  --user ROBOT_USER     User name for BasicAuth authentification. Default value is 'admin'
  --pass ROBOT_PASS     password for BasicAuth authentification. Default value is 'admin'
  --keyfile ROBOT_KEYFILE
                        SSL private key for secure communication. Default value is 'privkey.pem'
  --certfile ROBOT_CERTFILE
                        SSL certfile for secure communication. Default value is 'cacert.pem'
  --log-level {TRACE,NONE,DEBUG,INFO,WARN}
                        Robot Framework log level. Valid values = TRACE, DEBUG, INFO, WARN, NONE. Default value = WARN
  --debug               Enables debug logging and will not delete the temporary directory after a robot run
```

## Testing

### Certificate generation

- Run the [genpubkey.sh](https://github.com/joergschultzelutter/robotframework-remoterunner-mt/blob/master/src/genpubkey.sh) script.
- For testing on localhost, you can keep all defaults as is. Exception: set the ```FQDN``` setting to value ```localhost``` for both certificates

### Testing on localhost

Remember to set the following environment variables for __both__ server _and_ client sessions:

```bash
    export SSL_CERT_FILE=/path/to/your/cacert.pem
    export REQUESTS_CA_BUNDLE=/path/to/your/cacert.pem
```
