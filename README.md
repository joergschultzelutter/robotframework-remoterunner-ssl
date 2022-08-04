# robotframework-remoterunner-ssl

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![CodeQL](https://github.com/joergschultzelutter/robotframework-remoterunner-mt/actions/workflows/codeql.yml/badge.svg)](https://github.com/joergschultzelutter/robotframework-remoterunner-mt/actions/workflows/codeql.yml)

This is a Python3 port of [chrisBrookes93](https://github.com/chrisBrookes93)'s [robotframework-remoterunner](https://github.com/chrisBrookes93/robotframework-remoterunner) to  [Etopian](https://github.com/etopian/)'s [https XMLRPC server](https://github.com/etopian/python3-xmlrpc-ssl-basic-auth), providing a multithreaded XMLRPC SSL server with BasicAuth support and automated remote server PyPi package installation to Robot Framework users.

## Repository contents

The ```src``` directory from this repo contains two core scripts:

- ```server.py``` - The server that receives and executes the robot run
- ```client.py``` - The client that invokes the server to execute the robot run on a remote machine

### client.py

```text
usage: client.py [-h] [--test-connection] [--host ROBOT_HOST] [--port ROBOT_PORT] [--user ROBOT_USER] 
                      [--pass ROBOT_PASS] [--log-level {WARN,DEBUG,TRACE,NONE,INFO}] 
                      [--suite ROBOT_SUITE [ROBOT_SUITE ...]]
                      [--test ROBOT_TEST [ROBOT_TEST ...]] [--include ROBOT_INCLUDE [ROBOT_INCLUDE ...]] 
                      [--exclude ROBOT_EXCLUDE [ROBOT_EXCLUDE ...]] [--extension ROBOT_EXTENSION [ROBOT_EXTENSION ...]]
                      [--output-dir ROBOT_OUTPUT_DIR] [--input-dir ROBOT_INPUT_DIR [ROBOT_INPUT_DIR ...]] 
                      [--output-file ROBOT_OUTPUT_FILE] [--log-file ROBOT_LOG_FILE] [--report-file ROBOT_REPORT_FILE] [--debug]

options:
  -h, --help            show this help message and exit
  --test-connection     Enable this option to check if both client and server are properly configured. 
                        Returns a simple 'ok' string to the client if it was able to establish a secure connection to the remote
                        XMLRPC server and supplied user/pass credentials were ok
  --host ROBOT_HOST     IP or Hostname of the server to execute the robot run on. Default value = localhost
  --port ROBOT_PORT     Port number of the server to execute the robot run on. Default value = 8111
  --user ROBOT_USER     Server user name. Default value = admin
  --pass ROBOT_PASS     Server user passwort. Default value = admin
  --log-level {WARN,DEBUG,TRACE,NONE,INFO}
                        Threshold level for logging. Available levels: TRACE, DEBUG, INFO (default), WARN, NONE (no logging). 
                        Use syntax `LOGLEVEL:DEFAULT` to define the default visible log level in log
                        files. Examples: --loglevel DEBUG --loglevel DEBUG:INFO
  --suite ROBOT_SUITE [ROBOT_SUITE ...]
                        Select test suites to run by name. When this option is used with --test, --include or --exclude, only test 
                        cases in matching suites and also matching other filtering criteria are selected. Name can be a simple 
                        pattern similarly as with --test and it can contain parent name separated with a dot. You can specify 
                        this parameter multiple times, if necessary.
  --test ROBOT_TEST [ROBOT_TEST ...]
                        Select test cases to run by name or long name. Name is case insensitive and it can also be a simple 
                        pattern where `*` matches anything and `?` matches any char. You can specify this parameter multiple 
                        times, if necessary.
  --include ROBOT_INCLUDE [ROBOT_INCLUDE ...]
                        Select test cases to run by tag. Similarly as name with --test, tag is case and space insensitive and 
                        it is possible to use patterns with `*` and `?` as wildcards. Tags and patterns can also be combined 
                        together with `AND`, `OR`, and `NOT` operators. 
                        Examples: --include foo, --include bar*, --include fooANDbar*
  --exclude ROBOT_EXCLUDE [ROBOT_EXCLUDE ...]
                        Select test cases not to run by tag. These tests are not run even if included with --include. Tags 
                        are matched using the rules explained with --include.
  --extension ROBOT_EXTENSION [ROBOT_EXTENSION ...]
                        Parse only files with this extension when executing a directory. Has no effect when running individual
                        files or when using resource files. You can specify this parameter multiple times, if necessary. Specify
                        the value without leading '.'. Example: `--extension robot`. Default values: robot, text, txt, resource
  --output-dir ROBOT_OUTPUT_DIR
                        Output directory which will host your output files. If a nonexisting dictionary is specified, 
                        it will be created for you. Default value: current directory
  --input-dir ROBOT_INPUT_DIR [ROBOT_INPUT_DIR ...]
                        Input directory (containing your robot tests). You can specify this parameter multiple 
                        times, if necessary. Default value: current directory
  --output-file ROBOT_OUTPUT_FILE
                        Robot Framework output file name. Default value: remote_output.xml
  --log-file ROBOT_LOG_FILE
                        Robot Framework log file name. Default value: remote_log.html
  --report-file ROBOT_REPORT_FILE
                        Robot Framework report file name. Default value: remote_report.html
  --debug               Run in debug mode. This will enable debug logging and does not cleanup the workspace directory 
                        on the remote machine after test execution
```

If no parameters are specified, the ```client.py``` script will connect to a server on ```localhost``` port ```8111``` while serving all robot files from the current directory

### server.py

```text
usage: server.py [-h] [--host ROBOT_HOST] [--port ROBOT_PORT] [--user ROBOT_USER] 
                 [--pass ROBOT_PASS] [--keyfile ROBOT_KEYFILE] 
                 [--certfile ROBOT_CERTFILE] [--log-level {TRACE,WARN,NONE,DEBUG,INFO}]
                 [--always-upgrade-packages] [--debug]

options:
  -h, --help            show this help message and exit
  --host ROBOT_HOST     Address to bind to. Default is 'localhost'
  --port ROBOT_PORT     Port to listen on. Default is 8111
  --user ROBOT_USER     User name for BasicAuth authentification. Default value is 'admin'
  --pass ROBOT_PASS     password for BasicAuth authentification. Default value is 'admin'
  --keyfile ROBOT_KEYFILE
                        SSL private key for secure communication. Default value is 'privkey.pem'
  --certfile ROBOT_CERTFILE
                        SSL certfile for secure communication. Default value is 'cacert.pem'
  --log-level {TRACE,WARN,NONE,DEBUG,INFO}
                        Robot Framework log level. Valid values = TRACE, DEBUG, INFO, WARN, NONE. 
                        Default value = WARN
  --always-upgrade-packages
                        If your Robot Framework suite depends on external pip packages, 
                        always upgrade these packages even if they are already installed
  --debug               Enables debug logging and will not delete the temporary directory
                        after a robot run
```

## In scope

Supports all features that are supported by Chris' [robotframework-remoterunner](https://github.com/chrisBrookes93/robotframework-remoterunner) repository. Additional features and bug fixes:

- multithreaded https connection with both certificate and BasicAuth support
- fixed error with Library / Resource statements and trailing comments
- support for automated pip package installation on a remote server (see separate chapter)

## Out of scope

- Support for Python version 2

## Connection Test

For a simple connection test between ```Client``` and ```Server```, install programs, environment variables and certificates (see following chapters). Run the server. Then run the client with the ```--test-connection``` option:

```bash
(venv) [20:52:52 - jsl@gowron - ~/git/robotframework-remoterunner-ssl/src]$ python client.py --test-connection
2022-08-04 20:53:06,690 client -INFO- Connecting to: localhost:8111
2022-08-04 20:53:06,762 client -INFO- OK
```
If a SSL connection could be established and there was no mismatch in user/passwords, you should receive a plain 'OK' string.

## Library and Resource references for external files

Chris's original code already supported external references for:

- external resource files
- external python files

Examples:

```robotframework
*** Settings ***

Resource        robot_resource.resource
Library         python_file.py

```
Robot Framework standard libraries are detected and will obviously not be read from disk

## Support for auto-installation of PyPi packages on the remote server

### Introduction

If your Robot Framework suite depends on PyPi package libraries which are currently _not_ installed on the remote XMLRPC server, the previous lookup process would fail.

```robotframework
Library         Uninstalled_PyPi_Library
```

In order to support this use case, both ```Server```/```Client``` processes use a decorator-like reference. Let's extend the previous example with that decorator:

```robotframework
*** Settings ***

Resource        robot_resource.resource
Library         python_file.py
Library         AppriseLibrary # @pip:robotframework-apprise	
```

To summarize: in order to enable PyPi package installation process via pip, you need to do the following:

1. Specify your ```Library``` reference as usual

```robotframework
Library         AppriseLibrary	
```
2. Add a trailing comment with a decorator to that line. Specify the name of the package as listed on PyPi.

```robotframework
Library         AppriseLibrary 	# @pip:robotframework-apprise	
```
Syntax: ```@pip:<PyPi-Package-Name>[pypi version]``` 

Standard pip versioning is supported; just extend the decorator setting:

```robotframework
Library         AppriseLibrary # @pip:robotframework-apprise==0.1.0	
```

Leading / trailing comments etc are ignored by the decorator parser, meaning that a decorator setting like the following would still be successful:

```robotframework
Library         AppriseLibrary               ##### Hello @pip:robotframework-aprslib==0.1.0 World	
```

### Tell me more about what happens under the hood

- Client process examines Robot code suites / tests
- All ```Library``` references which do __not__ refer to external files (e.g. local Python files) and are __not__ part of the Robot Framework standard libraries will be cached by the ```Client``` and later on sent to the ```Server``` (similar to the file-based dependencies)
- Prior to processing the actual Robot Framework suites and tests, the ```Server``` process has a look at the pip package reference directory from the ```Client```:
    - Each entry in this directory will be checked against the PyPi packages that are installed on the server's Python environment.
    - If the package is detected as 'installed', the ```Server``` process will not reinstall the package. 
    - A version check between installed package version on the ```Server``` and expected package version from the ```Client's``` test suite will __NOT__ be performed
    - If you depend on always using the correct PyPi package version (regardless of whether the PyPi package is installed on the server or not), then activate the ```Server's``` ```--always-upgrade-packages``` option. __Note that this option might cause unintended side effects in case you run more than one test in parallel and re-install PyPi dependencies which are in use by one of your running tasks.__ 
    - If PyPi packages were detected to be installed, the ```Server``` temporarily unsets both ```SSL_CERT_FILE``` and ```REQUESTS_CA_BUNDLE``` environment variables as otherwise, the installation process would fail.
    - The ```Server``` now installs the requested PyPi packages and restores both ```SSL_CERT_FILE``` and ```REQUESTS_CA_BUNDLE``` environment variables' values
- Finally, the Robot Framework Suite(s) are executed as usual

## Testing

### Certificate generation

- Run the [genpubkey.sh](https://github.com/joergschultzelutter/robotframework-remoterunner-mt/blob/master/src/genpubkey.sh) script.
- For testing on localhost, you can keep all defaults as is. Exception: set the ```FQDN``` setting to value ```localhost``` for both certificates
- In case you use self-signed certificates for testing on ```localhost```, remember that you may be required set the following environment variables for __both__ ```Server``` _and_ ```Client``` sessions:

```bash
    export SSL_CERT_FILE=/path/to/your/cacert.pem
    export REQUESTS_CA_BUNDLE=/path/to/your/cacert.pem
```

In order to allow OpenSSL to trust your recently hatched self-signed certificate, you may need to apply a few more OS-specific steps. Details: see post on [StackOverflow](https://stackoverflow.com/questions/17437100/how-to-avoid-the-tlsv1-alert-unknown-ca-error-in-libmproxy)

#### Windows

See [https://docs.microsoft.com/en-US/troubleshoot/windows-server/identity/export-root-certification-authority-certificate](https://docs.microsoft.com/en-US/troubleshoot/windows-server/identity/export-root-certification-authority-certificate)

#### Linux

##### Installation

```bash
sudo mkdir /etc/share/certificates/extra && cp cacert.crt /user/share/certficates/extra/cacert.crt
sudo dpkg-reconfigure ca-certificates
```

##### Uninstall

```bash
sudo rm -r /etc/share/certificates/extra
sudo dpkg-reconfigure ca-certificates
```

### MacOS

##### Installation
```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain cacert.pem
```

##### Uninstall
```bash
sudo security remove-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain cacert.pem
```
