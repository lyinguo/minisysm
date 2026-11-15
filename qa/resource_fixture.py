"""Temporary resource grants in the verified disposable QA Redis only."""
import base64
import hashlib
import json
import re
import subprocess
from contextlib import contextmanager


def authority(identifier,keyword):
    if keyword and keyword.strip():return keyword
    compact=identifier.replace('-','')
    raw=bytes.fromhex(compact) if re.fullmatch('[0-9a-fA-F]{32}',compact) else hashlib.sha256(identifier.encode()).digest()[:16]
    return 'R_'+base64.urlsafe_b64encode(raw).decode().rstrip('=')


@contextmanager
def qa_resource_grants(state,paths,roles):
    assert re.fullmatch('psi_qa_[0-9a-f]{12}',state['database'])
    container='psi-qa-redis-'+state['database'][len('psi_qa_'):]
    actual=subprocess.run(['docker','ps','--filter','publish=18379','--format','{{.Names}}'],capture_output=True,text=True,check=True).stdout.strip()
    assert actual==container,'Refusing to alter unverified Redis'
    def redis(*args):return subprocess.run(['docker','exec',container,'redis-cli','--raw']+list(args),capture_output=True,text=True,check=True).stdout.rstrip('\r\n')
    previous={path:(redis('HEXISTS','AUTH:RESOURCE_ROLES',path),redis('HGET','AUTH:RESOURCE_ROLES',path)) for path in paths}
    try:
        for path in paths:redis('HSET','AUTH:RESOURCE_ROLES',path,json.dumps(['java.util.ArrayList',roles]))
        yield
    finally:
        for path,(exists,value) in previous.items():
            if exists=='1':redis('HSET','AUTH:RESOURCE_ROLES',path,value)
            else:redis('HDEL','AUTH:RESOURCE_ROLES',path)
