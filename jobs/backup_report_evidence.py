#!env python3

import argparse
import datetime
import json
import logging
import os
import pdfkit
import requests
from requests.auth import HTTPBasicAuth
from requests_toolbelt.multipart.encoder import MultipartEncoder
import sys

from auth import SecretStore

logging.basicConfig(format='%(asctime)s <%(name)s:%(levelname)s> %(message)s',
                    level=logging.INFO)
_log = logging.getLogger(os.path.basename(__file__))

parser = argparse.ArgumentParser()
parser.add_argument('--date')
parser.add_argument('--username')
parser.add_argument('--password')
parser.add_argument('name')
args = parser.parse_args()

pdf_msg = pdfkit.from_string(sys.stdin.read())

ss = SecretStore()
secrets = ss.get('external/onetrust/backup-reports')

collected_date = datetime.date.today()
if args.date:
        collected_date = datetime.date.fromisoformat(args.date.split('T')[0])

url = 'https://openapi.tugboatlogic.com/api/v0/evidence/collector/30042/'
payload = MultipartEncoder(
        fields={'collected': collected_date.isoformat(),
                # send evidence file (CSV document) here
                'file': (f'backup_report-{collected_date.isoformat()}-{args.name}.pdf', pdf_msg,
                        ('application/pdf')),
               }
        )
headers = {'X-API-KEY': secrets.get('api_key'),
           'Content-Type': payload.content_type}

try:
        response = requests.post(url,
                                auth=HTTPBasicAuth(secrets.get('username'), secrets.get('password')),
                                headers=headers,
                                data=payload)

        evidence = json.loads(response.text)
        if "id" in evidence:
                _log.info(f"Uploaded to Tugboat Logic: Evidence {evidence['id']}")
        else:
                _log.critical(evidence['detail'])
                sys.exit(-1)
        
except Exception as e:
        _log.critical(e)
        sys.exit(-2)