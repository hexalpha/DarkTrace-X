import json
import logging
from datetime import UTC,datetime


class SafeJSONFormatter(logging.Formatter):
    def format(self,record):
        from app.services.copilot_store import redact
        result={'timestamp':datetime.now(UTC).isoformat(),'level':record.levelname,'message':redact(record.getMessage())}
        for name in ('request_id','tenant_id','source_id','crawl_id','job_id','duration_ms','error_type'):
            result[name]=getattr(record,name,None)
        return json.dumps(result,default=str)


def configure_logging():
    logger=logging.getLogger('app')
    handler=logging.StreamHandler();handler.setFormatter(SafeJSONFormatter())
    logger.handlers=[handler];logger.setLevel(logging.INFO);logger.propagate=False
