import hvac
import logging
import os

class SecretStore(object):

    client = None

    def __init__(self, token=None, mountpoint="kv", loglevel=logging.INFO):
        self._log = logging.getLogger("z0vault")
        self._log.setLevel(level=loglevel)

        client_token = token
        if client_token is None:
            client_token = os.environ.get("VAULT_TOKEN")

        self.mountpoint = mountpoint

        self.client = hvac.Client(url=os.environ.get("VAULT_ADDR"))
        self.client.token = client_token

    def get(self, path):
        read_response = self.client.secrets.kv.v2.read_secret_version(path=path,
                                                                      mount_point=self.mountpoint)

        self._log.debug(read_response)
        return read_response['data']['data']