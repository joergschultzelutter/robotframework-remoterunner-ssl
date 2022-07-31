# robotframework-remoterunner-mt

This is a blend of [chrisBrookes93](https://github.com/chrisBrookes93)'s [robotframework-remoterunner](https://github.com/chrisBrookes93/robotframework-remoterunner)and the [XMLRPC SSL Basic Auth](https://github.com/etopian/python3-xmlrpc-ssl-basic-auth) XMLRPC SSL server from [Etopian](https://github.com/etopian/), providing a remote multithreaded XMLRPC SSL server with basic auth authorization to Robot Framework users. 

## Generate the certificates

Run the [genpubkey.sh](https://github.com/joergschultzelutter/robotframework-remoterunner-mt/blob/master/src/genpubkey.sh) script.

## Testing on localhost

- When generating the certificates, set the FQDN to 'localhost' for both certificates
- Set the following environment variables for __both__ server _and_ client sessions:

```bash
    export SSL_CERT_FILE=/path/to/your/cacert.pem
    export REQUESTS_CA_BUNDLE=/path/to/your/cacert.pem
```
