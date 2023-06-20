
import logging

class EvidenceCollectorNotSupported(Exception):
    pass


class EvidenceCollector(object):

    def __init__(self, collector_id=None, loglevel=logging.DEBUG, collectortype=None, **collector_settings):
        self.collector_id = collector_id
        self.type = collectortype

        self._log = logging.getLogger("z0evidence")
        self._log.setLevel(level=loglevel)
