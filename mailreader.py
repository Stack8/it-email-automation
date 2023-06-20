
import argparse
import logging
import os
import sys
from auth import SecretStore
from mailhandler import DispatchRules
from mailhandler import O365Mailbox
from datetime import date

parser = argparse.ArgumentParser()
parser.add_argument('--debug', help="Enable debugging", action='store_true')
parser.add_argument('--mailbox', help="Which mailbox to read", required=True)
parser.add_argument('--vault', help="Get account credentials from this vault KV mount")
parser.add_argument('--date', help="Parse emails as-of date")
args = parser.parse_args()

_log = logging.getLogger(__file__)
loglevel = logging.INFO
if args.debug:
    loglevel=logging.DEBUG
    _log.setLevel(level=loglevel)
logging.basicConfig(format='%(asctime)s <%(name)s:%(levelname)s> %(message)s',
                    level=loglevel)

fromdate = None
if args.date:
    try:
        fromdate = date.fromisoformat(args.date)
    except Exception:
        raise

secrets = None
if args.vault:
    ss = SecretStore(loglevel=loglevel)
    secrets = ss.get(args.vault)
else:
    secrets = []
    secrets['TENANT_ID'] = os.environ.get('ARM_TENANT_ID')
    secrets['CLIENT_ID'] = os.environ.get('ARM_CLIENT_ID')
    secrets['CLIENT_SECRET'] = os.environ.get('ARM_CLIENT_SECRET')

rules = DispatchRules('rules.yaml', loglevel=loglevel)

mailbox = O365Mailbox(tenant=secrets.get('TENANT_ID'),
                      client_id=secrets.get('CLIENT_ID'),
                      client_secret=secrets.get('CLIENT_SECRET'),
                      user_id=args.mailbox,
                      loglevel=loglevel)

messages = mailbox.list(date=fromdate)
for msg in messages:
    try:
        processed = rules.process(msg)
        if processed:
            mailbox.delete(msg)
    except Exception as e:
        raise