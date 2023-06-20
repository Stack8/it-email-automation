
import logging
import os
import yaml
import re

from yaml.loader import SafeLoader

from task.evidencecollector import EvidenceCollectorNotSupported
from task.supported_evidence import SUPPORTED_EVIDENCE


class NoRulesException(Exception):
    pass


class DispatchRules(object):

    sanitizing = re.compile('^(?P<arg>[a-z0-9_]+).*')

    def __init__(self, rules, loglevel=logging.INFO):
        self.rules = {}

        self._log = logging.getLogger("z0ruledispatcher")
        self._log.setLevel(level=loglevel)

        self.evidence_collectors = {}

        if isinstance(rules, str):
            with open(rules, 'r') as f:
                yamlrules = yaml.load(f, Loader=SafeLoader)
                self.rules = yamlrules['rules']

                if 'evidence_collectors' in yamlrules:
                    try:
                        self.evidence_collectors = self._build_collectors(yamlrules['evidence_collectors'])
                    except:
                        raise

        else:
            self.rules.extend(rules)

        self._log.debug(f"Effective rules: {self.rules}")
        self._log.info(f"Evidence collectors: {self.evidence_collectors}")

    def _build_collectors(self, collector_entries):
        collectors = {}

        for collector in collector_entries:
            self._log.debug(collector)

            collector_id = collector.get('id')
            type = collector.get('type')

            if type not in SUPPORTED_EVIDENCE:
                raise EvidenceCollectorNotSupported()

            else:
                c = SUPPORTED_EVIDENCE[type](collector_id=collector_id, **collector)
                collectors[collector_id] = c

        return collectors

    def __getitem__(self, item):
         return self.rules[item]

    def __str__(self):
        return str(self.rules)

    def _filter_rules(self, email):
        filtered_rules = []

        sender = email.sender
        subject = email.subject

        if sender in self.rules['senders']:
            filtered_rules.extend(self.rules['senders'][sender])
        for subject_match in self.rules['subjects']:
            if re.fullmatch(subject_match, subject):
                filtered_rules.extend(self.rules['subjects'][subject_match])

        self._log.debug(f"[{email.zid}] Filtered rules: {filtered_rules}")
        return filtered_rules

    def process(self, email):
        try:
            sender = email.sender
            subject = email.subject

            self._log.info(f"[{email.zid}] Processing email: {email.__repr__()}")
            filtered_rules = self._filter_rules(email)

            if len(filtered_rules) < 1:
                raise NoRulesException("[{email.zid}] no suitable rules")

            for rule in filtered_rules:
                self._eval_rule(rule, email)

            return True
        except NoRulesException:
            self._log.debug(f"[{email.zid}] Processed email ignored; did not match any rule")
            return False
        except Exception as e:
            self._log.error(f"[{email.zid}] Processing failed: {e}")
            return False

    def _eval_rule(self, rule, email, loglevel=logging.INFO):
        #logging.basicConfig(format='%(asctime)s <%(name)s:%(levelname)s> %(message)s',
        #                    level=loglevel)
        self._log = logging.getLogger("z0ruledispatcher.rule")

        self._log.debug(f"[{email.zid}] Rule matched: {rule}")

        match rule['type']:
            case "script":
                try:
                    import subprocess
                    import tempfile

                    em_tmpfile = tempfile.NamedTemporaryFile(delete=False)
                    em_tmpfile.write(email.content.encode('utf-8'))
                    em_tmpfile.seek(0)

                    cmd = ['python3', os.path.join('.', rule['script'])]
                    params = rule.get('params', {})
                    for p in params:
                        str_eval = "email." + re.match(cls.sanitizing, params[p]).group('arg')
                        add_arg = eval(str_eval)
                        cmd.append(p)
                        cmd.append(add_arg)

                    cmd.append(email.zid)

                    self._log.info(f"[{email.zid}] Running {cmd}")
                    job = subprocess.run(cmd, stdin=em_tmpfile)
                    job.check_returncode()
                except Exception as e:
                    raise

            case "evidence":
                self._log.debug(f'[{email.zid}] Capturing evidence.')
                self.evidence_collectors[rule['collector']].collect(email)

            case "noop":
                self._log.debug(f'[{email.zid}] No action.')
