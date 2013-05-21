import httplib
import logging
from urlparse import urlparse

from nss.error import NSPRError
import nss.io as io
import nss.nss as nss
import nss.ssl as ssl
from pysimplesoap import transport


class NSSConnection(httplib.HTTPConnection):
    default_port = httplib.HTTPSConnection.default_port

    def __init__(self, host, port=None, strict=None, dbdir=None, cert_name=None):
        httplib.HTTPConnection.__init__(self, host, port, strict)

        if not dbdir:
            raise RuntimeError("dbdir is required")

        logging.debug('%s init %s', self.__class__.__name__, host)
        if not nss.nss_is_initialized():
            nss.nss_init(dbdir)

        self.sock = None
        self.cert_name = cert_name
        ssl.set_domestic_policy()

    def _create_socket(self, family):
        self.sock = ssl.SSLSocket(family)
        self.sock.set_ssl_option(ssl.SSL_SECURITY, True)
        self.sock.set_ssl_option(ssl.SSL_HANDSHAKE_AS_CLIENT, True)
        self.sock.set_hostname(self.host)

        # Provide a callback which notifies us when the SSL handshake is complete
        self.sock.set_handshake_callback(self.handshake_callback)
        self.sock.set_client_auth_data_callback(self.client_auth_data_callback, self.cert_name)
        self.sock.set_auth_certificate_callback(self.auth_certificate_callback)

    def connect(self):
        logging.debug("connect: host=%s port=%s", self.host, self.port)
        try:
            addr_info = io.AddrInfo(self.host)
        except Exception, e:
            logging.error("could not resolve host address \"%s\"", self.host)
            raise

        for net_addr in addr_info:
            net_addr.port = self.port
            self._create_socket(net_addr.family)
            try:
                logging.debug("try connect: %s", net_addr)
                self.sock.connect(net_addr, timeout=io.seconds_to_interval(30))
                logging.debug("connected to: %s", net_addr)
                return
            except Exception, e:
                logging.debug("connect failed: %s (%s)", net_addr, e)

        raise IOError(errno.ENOTCONN, "could not connect to %s at port %d" % (self.host, self.port))

    def handshake_callback(self, sock):
        logging.debug("handshake complete, peer = %s" % (sock.get_peer_name()))

    def client_auth_data_callback(self, sock, name):
        try:
            cert = nss.find_cert_from_nickname(name)
            priv_key = nss.find_key_by_any_cert(cert)
            return cert, priv_key
        except NSPRError, e:
            logging.debug("client authentication failed: %s", e)
            return False

    def auth_certificate_callback(self, sock, check_sig, is_server):
        cert_is_valid = False
        certdb = nss.get_default_certdb()

        cert = sock.get_peer_certificate()

        logging.debug("auth_certificate_callback: check_sig=%s is_server=%s\n%s",
                      check_sig, is_server, str(cert))

        pin_args = sock.get_pkcs11_pin_arg()
        if pin_args is None:
            pin_args = ()

        intended_usage = nss.certificateUsageSSLServer

        try:
            # If the cert fails validation it will raise an exception, the errno attribute
            # will be set to the error code matching the reason why the validation failed
            # and the strerror attribute will contain a string describing the reason.
            approved_usage = cert.verify_now(certdb, check_sig, intended_usage, *pin_args)
        except Exception, e:
            logging.error('cert validation failed for "%s" (%s)', cert.subject, e.strerror)
            cert_is_valid = False
            return cert_is_valid

        logging.debug("approved_usage = %s intended_usage = %s",
                      ', '.join(nss.cert_usage_flags(approved_usage)),
                      ', '.join(nss.cert_usage_flags(intended_usage)))

        # Is the intended usage a proper subset of the approved usage
        if approved_usage & intended_usage:
            cert_is_valid = True
        else:
            cert_is_valid = False

        # If this is a server, we're finished
        if is_server or not cert_is_valid:
            logging.debug('cert valid %s for "%s"', cert_is_valid,  cert.subject)
            return cert_is_valid

        # Certificate is OK.  Since this is the client side of an SSL
        # connection, we need to verify that the name field in the cert
        # matches the desired hostname.  This is our defense against
        # man-in-the-middle attacks.

        hostname = sock.get_hostname()
        try:
            # If the cert fails validation it will raise an exception
            cert_is_valid = cert.verify_hostname(hostname)
        except Exception, e:
            logging.error('failed verifying socket hostname "%s" matches cert subject "%s" (%s)',
                          hostname, cert.subject, e.strerror)
            cert_is_valid = False
            return cert_is_valid

        logging.debug('cert valid %s for "%s"', cert_is_valid,  cert.subject)
        return cert_is_valid


class NSSTransport(object):
    class NSSTransport(transport.TransportBase):
        _wrapper_version = "NSS 0.1"
        _wrapper_name = 'NSS'
        def __init__(self, timeout=None, proxy=None, cacert=None, sessions=False):
                       
            self._timeout = timeout

        def request(self, url, method="GET", body=None, headers={}):
            urlparts = urlparse(url)
            conn = NSSConnection(urlparts.hostname, urlparts.port, True, self.dbdir, self.cert_name)
            conn.request(method, u'%s?%s' % (urlparts.path, urlparts.query), body, headers)
            try:
                r = conn.getresponse()
            except httplib.HTTPException:
                if r.status != 500:
                    raise
            data = r.read()
            return r.status, data

    def __init__(self, dbdir, client_cert_name):
        self.NSSTransport.dbdir = dbdir
        self.NSSTransport.cert_name = client_cert_name

        transport._http_connectors['nss'] = self.NSSTransport
        transport.set_http_wrapper('nss')
