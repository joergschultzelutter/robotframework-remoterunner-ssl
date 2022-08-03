# robotframework-remoterunner-mt

This is a port of [chrisBrookes93](https://github.com/chrisBrookes93)'s [robotframework-remoterunner](https://github.com/chrisBrookes93/robotframework-remoterunner) to  [Etopian](https://github.com/etopian/)'s [XMLRPC server](https://github.com/etopian/python3-xmlrpc-ssl-basic-auth), providing a remote multithreaded XMLRPC SSL server with basic auth authorization to Robot Framework users. 

## Certificate generation

- Run the [genpubkey.sh](https://github.com/joergschultzelutter/robotframework-remoterunner-mt/blob/master/src/genpubkey.sh) script.
- For testing on localhost, you can keep all defaults as is. Exception: set the ```FQDN``` setting to value ```localhost``` for both certificates

## Testing on localhost

Remember to set the following environment variables for __both__ server _and_ client sessions:

```bash
    export SSL_CERT_FILE=/path/to/your/cacert.pem
    export REQUESTS_CA_BUNDLE=/path/to/your/cacert.pem
```
