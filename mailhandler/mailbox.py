
import msal
import requests
import logging
import hashlib
from datetime import date


class CleanupException(Exception):
    pass


class EmailMessage(object):

    def __init__(self, emaildata):
        self.message_id = emaildata['id']
        self.short_id = hashlib.sha1(self.message_id.encode('utf-8')).hexdigest()[0:8]
        try:
            self.sender_name = emaildata['sender']['emailAddress']['name']
            self.sender_email = emaildata['sender']['emailAddress']['address']
            self.received_date = emaildata['receivedDateTime']
            self.subj = emaildata['subject']
            self.body = emaildata['body']['content']
        except:
            print(emaildata)

    @property
    def id(self):
        return self.message_id

    @property
    def zid(self):
        return self.short_id

    @property
    def subject(self):
        return self.subj

    @property
    def sender(self):
        return self.sender_email

    @property
    def received(self):
        return self.received_date

    @property
    def content(self):
        return self.body

    def __repr__(self):
        return f'[{self.received}] "{self.subject}" (from "{self.sender_name}" <{self.sender_email}>)'

    def __str__(self):
        return self.body


class O365Mailbox(object):

    def __init__(self, tenant, client_id, client_secret, user_id, loglevel=logging.INFO):
        self._log = logging.getLogger("z0mailbox")
        self._log.setLevel(level=loglevel)

        self.authenticated = False
        
        result = None
        try:
            authority = f"https://login.microsoftonline.com/{tenant}"
            app = msal.ConfidentialClientApplication(
                    client_id=client_id,
                    client_credential=client_secret,
                    authority=authority)

            scopes = ["https://graph.microsoft.com/.default"]
            result = app.acquire_token_silent(scopes, account=None)
        except Exception as e:
            raise

        if not result:
            self._log.debug("No suitable token exists in cache. Let's get a new one from Azure Active Directory.")
            result = app.acquire_token_for_client(scopes=scopes)

        if "access_token" in result:
            self._log.debug("Authenticated successfully")
            self.access_token = result['access_token']
            self.user_id = user_id
            self.authenticated = True
            
    def list(self, date=None):
        if not self.authenticated:
            self._log.error("Not authenticated")
            raise O365Unauthenticated()
            
        endpoint = f'https://graph.microsoft.com/v1.0/users/{self.user_id}/messages?$select=sender,subject,body,receivedDateTime'

        params = {}
        if date:
            params = {
                "$filter": f"receivedDateTime lt {date.isoformat()}",
            }
        messages = []
        try:
            nextlink = endpoint
            while nextlink:
                r = requests.get(nextlink,
                                params=params,
                                headers={'Authorization': 'Bearer ' + self.access_token})
                if r.ok:
                    self._log.debug('Retrieved emails successfully')
                    data = r.json()
                    nextlink = data.get('@odata.nextLink', None)
                    params = None
                    for email in data['value']:
                        try:
                            msg = EmailMessage(email)
                            messages.append(msg)
                        except Exception as e:
                            self._log.debug(email)
                            raise
                else:
                    self._log.critical(r.json())
        except Exception as e:
            raise

        return messages

    def delete(self, message):
        endpoint = f'https://graph.microsoft.com/v1.0/users/{self.user_id}/messages/{message.id}'
        self._log.debug(f"[{message.zid}] Deleting message")
        r = requests.delete(endpoint,
                            headers={'Authorization': 'Bearer ' + self.access_token})
        if r.ok:
            self._log.info(f'[{message.zid}] Deleted message.')
        else:
            raise CleanupException(r)

        
