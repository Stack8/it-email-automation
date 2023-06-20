
import re
import json
import pdfkit
import requests
from requests.auth import HTTPBasicAuth
from requests_toolbelt.multipart.encoder import MultipartEncoder

from auth import SecretStore

from .evidencecollector import EvidenceCollector


class TBLEvidenceCollector(EvidenceCollector):

    def __init__(self, collector_id=None, **kwargs):
        super().__init__(collector_id=collector_id, collector_type="tugboatlogic", **kwargs)

        self.vault = kwargs.get('vault', None)
        self.username = kwargs.get('username', None)
        self.password = kwargs.get('password', None)
        self.api_key = kwargs.get('api_key', None)

        if self.vault:
            ss = SecretStore()
            secrets = ss.get(self.vault)
            self.username = secrets.get('username')
            self.password = secrets.get('password')
            self.api_key = secrets.get('api_key')
        
        self.url = f'https://openapi.tugboatlogic.com/api/v0/evidence/collector/{self.collector_id}/'

    def collect(self, email):
        id = email.zid
        date = email.received.split('T')[0]

        mailto_url = re.compile('mailto:.*\"')
        cid_url = re.compile('cid:.*\"')
        tel_url = re.compile('tel:.*\"')

        content = email.content
        content = mailto_url.sub('', content)
        content = cid_url.sub('', content)
        content = tel_url.sub('', content)
        
        pdf_msg = pdfkit.from_string(content,
                                     options={"images": ""})                
        
        try:
            payload = MultipartEncoder(
                    fields={'collected': date,
                            'file': (f'evidence-{date}-{id}.pdf', pdf_msg,
                                    ('application/pdf')),
                        }
                    )

            headers = {'X-API-KEY': self.api_key,
                    'Content-Type': payload.content_type}

            response = requests.post(self.url,
                                     auth=HTTPBasicAuth(self.username, self.password),
                                     headers=headers,
                                     data=payload)

            evidence = json.loads(response.text)
            if "id" in evidence:
                    self._log.info(f"Uploaded to Tugboat Logic: Evidence {evidence['id']}")
            else:
                    self._log.critical(evidence['detail'])

            return True
                
        except Exception as e:
            self._log.critical(e)
            raise

