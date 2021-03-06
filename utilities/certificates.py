# -*- coding: utf-8 -*-

"""
Using x509 certificates
"""

import os
import re
import pytz
from datetime import datetime, timedelta

from utilities.basher import BashCommands
from utilities import htmlcodes as hcodes
from utilities.uuid import getUUID
from utilities.logs import get_logger

log = get_logger(__name__)

try:
    from OpenSSL import crypto
    from plumbum import local
    import dateutil.parser
except ImportError as e:
    log.critical_exit("\nThis module requires an extra package:\n%s", e)


class Certificates(object):

    _dir = os.environ.get('CERTDIR')
    _proxyfile = 'userproxy.crt'

    @classmethod
    def get_dn_from_cert(cls, certdir, certfilename, ext='pem'):

        dn = ''
        cpath = os.path.join(cls._dir, certdir, "%s.%s" % (certfilename, ext))
        content = open(cpath).read()
        cert = crypto.load_certificate(crypto.FILETYPE_PEM, content)
        sub = cert.get_subject()

        for tup in sub.get_components():
            dn += '/' + tup[0].decode() + '=' + tup[1].decode()

        log.verbose("Host DN computed is %s", dn)
        return dn

    @classmethod
    def get_proxy_filename(cls, user, dirname=False):
        if dirname:
            return "%s/%s" % (cls._dir, user)
        return "%s/%s/%s" % (cls._dir, user, cls._proxyfile)

    @staticmethod
    def proxy_write(tmpproxy, destination_path):

        from shutil import copyfile
        # NOTE: trhows error if files do not exist
        copyfile(tmpproxy, destination_path)
        # NOTE: use the octave from the UNIX 'mode'
        os.chmod(destination_path, 0o600)

    def save_proxy_cert(self, tmpproxy, unityid='guest', user=None):

        destination_path = self.get_proxy_filename(unityid)

        from utilities.helpers import parent_dir
        destination_dir = parent_dir(destination_path)
        if not os.path.exists(destination_dir):
            os.mkdir(destination_dir)

        # write the irods username inside as #/.username
        if user is not None:
            with open(os.path.join(destination_dir, '.username'), 'w') as f:
                f.write(user)

        self.proxy_write(tmpproxy, destination_path)
        return destination_path

    def encode_csr(self, req):
        enc = crypto.dump_certificate_request(crypto.FILETYPE_PEM, req)
        data = {'certificate_request': enc}
        return data

    @staticmethod
    def generate_csr_and_key(user='TestUser'):
        """
        TestUser is the user proposed by the documentation,
        which will be ignored
        """
        key = crypto.PKey()
        key.generate_key(crypto.TYPE_RSA, 1024)
        req = crypto.X509Req()
        req.get_subject().CN = user
        req.set_pubkey(key)
        req.sign(key, "sha1")
        # print("CSR", key, req)
        return key, req

    def write_key_and_cert(self, key, cert):
        proxycertcontent = cert.decode()
        if proxycertcontent is None or proxycertcontent.strip() == '':
            return None
        tempfile = "/tmp/%s" % getUUID()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        with os.fdopen(os.open(tempfile, flags, 0o600), 'w') as f:
            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key).decode())
            f.write(proxycertcontent)
        return tempfile

    def proxy_from_ca(self, ca_client, prod=False):
        """
        Request for certificate and save it into a file

        NOTE: insecure ssl context is required with b2access dev,
        because they do not have a valid HTTPS certificate for development
        """

        if not prod:
            # INSECURE SSL CONTEXT.
            # source: http://stackoverflow.com/a/28052583/2114395
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context  # nopep8 # pylint:disable=protected-access

        #######################
        key, req = self.generate_csr_and_key()
        # log.debug("Key and Req:\n%s\n%s" % (key, req))

        #######################
        response = None
        try:
            response = ca_client.post(
                'ca/o/delegateduser',
                data=self.encode_csr(req),
                headers={'Accept-Encoding': 'identity'})
            # Note: token is applied from oauth2 lib using the session content
        except ValueError as e:
            log.error("Oauthlib call with CA: %s", e)
            return None
        except Exception as e:
            # TODO: expand this case
            # 1. CA is unreachable (internet)
            # 2. CA says the token is invalid
            log.error("CA is probably down... [%s]", e)
            return None

        if response.status != hcodes.HTTP_OK_BASIC:
            # print("\nCertificate:"); log.pp(response)
            log.error("Could not get proxy from CA: %s", response.data)
            return None
        # log.pp(response)

        #######################
        # write proxy certificate to a random file name
        proxyfile = self.write_key_and_cert(key, response.data)
        log.debug('Wrote certificate to %s', proxyfile)

        return proxyfile

    def set_globus_ca_dir(self, xcdir):
        # CA CERTIFICATES DIR
        if xcdir is None:
            os.environ['X509_CERT_DIR'] = os.path.join(self._dir, 'simple_ca')
        else:
            os.environ['X509_CERT_DIR'] = xcdir

    def set_globus_proxy_cert(self, key, cert):  # , proxy=None):

        os.environ['X509_USER_KEY'] = key
        os.environ['X509_USER_CERT'] = cert

        # NOTE: for proxy we use above as temporary fix
        # check in the future why the right variable doesn't work anymore
        # os.environ['X509_USER_PROXY'] = proxy

    def globus_proxy(self,
                     proxy_file=None, user_proxy=None,
                     cert_dir=None, myproxy_host=None,
                     cert_name=None, cert_pwd=None):

        # Compute paths for certificates
        self.set_globus_ca_dir(cert_dir)
        cpath = os.path.join(self._dir, user_proxy)

        ################
        # 1. b2access
        if proxy_file is not None:
            log.debug("Certificate path: %s", proxy_file)
            self.set_globus_proxy_cert(key=proxy_file, cert=proxy_file)

        ################
        # 2. normal certificates (e.g. 'guest')
        elif os.path.isdir(cpath):
            self.set_globus_proxy_cert(
                key=os.path.join(cpath, 'userkey.pem'),
                cert=os.path.join(cpath, 'usercert.pem'))

        ################
        # 3. mattia's certificates?
        elif myproxy_host is not None:

            proxy_cert_file = cpath + '.pem'
            if not os.path.isfile(proxy_cert_file):
                # Proxy file does not exist
                valid = False
            else:
                valid, not_before, not_after = \
                    self.check_cert_validity(proxy_cert_file)
                if not valid:
                    log.warning(
                        "Invalid proxy certificate for %s." +
                        " Validity: %s - %s", user_proxy, not_before, not_after
                    )

            # Proxy file does not exist or expired
            if not valid:
                log.warning("Creating a new proxy for %s", user_proxy)
                try:

                    irods_env = os.environ

                    valid = Certificates.get_myproxy_certificate(
                        # FIXME: X509_CERT_DIR should be enough
                        irods_env=irods_env,
                        irods_user=user_proxy,
                        myproxy_cert_name=cert_name,
                        irods_cert_pwd=cert_pwd,
                        proxy_cert_file=proxy_cert_file,
                        myproxy_host=myproxy_host
                    )

                    if valid:
                        log.info("Proxy refreshed for %s", user_proxy)
                    else:
                        log.error("Got invalid proxy: user %s", user_proxy)

                except Exception as e:
                    log.critical("Cannot refresh proxy: user %s", user_proxy)
                    log.critical(e)

            ##################
            if valid:
                self.set_globus_proxy_cert(
                    key=proxy_cert_file, cert=proxy_cert_file)
            else:
                log.critical("Cannot find a valid certificate file")
                return False

        self.check_x509_permissions()

    def check_x509_permissions(self):

        from utilities import basher
        os_user = basher.current_os_user()
        failed = False

        # Check up with X509 variables
        for key, filepath in os.environ.items():

            # skip non certificates variables
            if not key.startswith('X509'):
                continue

            # check if current HTTP API user can read needed certificates
            if key.lower().endswith('cert_dir'):
                # here it has been proven to work even if not readable...
                if not basher.path_is_readable(filepath):
                    failed = True
                    log.error("%s variable (%s) not readable by %s",
                              key, filepath, os_user)
            else:
                os_owner = basher.file_os_owner(filepath)
                if os_user != os_owner:
                    failed = True
                    log.error("%s variable (%s) owned by %s instead of %s",
                              key, filepath, os_owner, os_user)

        if failed:
            raise AttributeError('Certificates ownership problem')

    @staticmethod
    def check_cert_validity(certfile, validity_interval=1):
        args = ["x509", "-in", certfile, "-text"]

        bash = BashCommands()
        # TODO: change the openssl bash command with the pyOpenSSL API
        # if so we may remove 'plumbum' from requirements of rapydo-http repo
        output = bash.execute_command("openssl", args)

        pattern = re.compile(
            r"Validity.*\n\s*Not Before: (.*)\n" +
            r"\s*Not After *: (.*)")
        validity = pattern.search(output).groups()

        not_before = dateutil.parser.parse(validity[0])
        not_after = dateutil.parser.parse(validity[1])
        now = datetime.now(pytz.utc)
        valid = \
            (not_before < now) and \
            (not_after > now - timedelta(hours=validity_interval))

        return valid, not_before, not_after

    @classmethod
    def get_myproxy_certificate(cls, irods_env,
                                irods_user, myproxy_cert_name, irods_cert_pwd,
                                proxy_cert_file,
                                duration=168,
                                myproxy_host="grid.hpc.cineca.it"
                                ):
        try:
            myproxy = local["myproxy-logon"]
            if irods_env is not None:
                myproxy = myproxy.with_env(**irods_env)

            # output = (myproxy[
            #     "-s", myproxy_host,
            #     "-l", irods_user,
            #     "-k", myproxy_cert_name,
            #     "-t", str(duration),
            #     "-o", proxy_cert_file, "-S"] << irods_cert_pwd)()
            # # log.critical(output)
            (
                myproxy[
                    "-s", myproxy_host,
                    "-l", irods_user,
                    "-k", myproxy_cert_name,
                    "-t", str(duration),
                    "-o", proxy_cert_file,
                    "-S"
                ] << irods_cert_pwd
            )()

            return True
        except Exception as e:
            log.error(e)
            return False
