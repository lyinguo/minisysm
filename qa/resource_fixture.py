"""Temporary resource grants in the verified disposable QA Redis only."""
import base64
import hashlib
import json
import re
import subprocess
import time
import uuid
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


@contextmanager
def qa_database_resource_grants(state,paths,roles):
    """Explicit disposable DB catalog/role fixtures; does not claim a role-UI lifecycle."""
    from acceptance import sql,literal
    assert re.fullmatch('psi_qa_[0-9a-f]{12}',state['database'])
    assert paths and all(path.startswith('/fund/receipt/') for path in paths)
    identifiers=[];previous={};menu=uuid.uuid4().hex;menu_created=False
    try:
        sql(state,'INSERT INTO menu(id,pid,name,`key`,model,type,resource,sort) VALUES('+','.join(literal(value) for value in [menu,'0','QA receipt permission fixture','qa-receipt-'+menu[:8],0,0,'',0])+');')
        menu_created=True
        for path in paths:
            identifier=uuid.uuid4().hex;identifiers.append(identifier)
            sql(state,'INSERT INTO func_perm(id,mid,name,url,sort,is_enable) VALUES('+','.join(literal(value) for value in [identifier,menu,'QA receipt permission fixture',path,0,'1'])+');')
        for keyword in roles:
            rows=json.loads(sql(state,'SELECT COALESCE(JSON_ARRAYAGG(JSON_OBJECT(\'id\',id,\'root_hex\',HEX(COALESCE(root,\'[]\')),\'name\',name)),JSON_ARRAY()) FROM role WHERE keyword='+literal(keyword)+';'))
            assert len(rows)==1 and rows[0]['name'].startswith('QA'),'Refusing to change a non-fixture role'
            row=rows[0];original=bytes.fromhex(row['root_hex']).decode('utf-8');previous[row['id']]=original;root=json.loads(original or '[]')
            assert isinstance(root,list)
            root.append(dict(id=menu,fun=[dict(id=identifier) for identifier in identifiers]))
            sql(state,'UPDATE role SET root='+literal(json.dumps(root))+' WHERE id='+literal(row['id'])+';')
        yield
    finally:
        for identifier,root in previous.items():
            sql(state,'UPDATE role SET root='+literal(root)+' WHERE id='+literal(identifier)+';')
        if identifiers:sql(state,'DELETE FROM func_perm WHERE mid='+literal(menu)+' AND id IN ('+','.join(literal(identifier) for identifier in identifiers)+');')
        if menu_created:sql(state,'DELETE FROM menu WHERE id='+literal(menu)+';')


@contextmanager
def qa_resource_cache_snapshot(state):
    """Restore the entire QA cache around real application reloads; never invent grants."""
    assert re.fullmatch('psi_qa_[0-9a-f]{12}',state['database'])
    container='psi-qa-redis-'+state['database'][len('psi_qa_'):]
    actual=subprocess.run(['docker','ps','--filter','publish=18379','--format','{{.Names}}'],capture_output=True,text=True,check=True).stdout.strip()
    assert actual==container,'Refusing to snapshot an unverified Redis'
    def redis(*args):return subprocess.run(['docker','exec',container,'redis-cli']+list(args),capture_output=True,text=True,encoding='utf-8',check=True).stdout.strip()
    previous=json.loads(redis('--json','HGETALL','AUTH:RESOURCE_ROLES'))
    if isinstance(previous,list):
        assert len(previous)%2==0;previous=dict(zip(previous[::2],previous[1::2]))
    assert isinstance(previous,dict) and all(isinstance(key,str) and isinstance(value,str) for key,value in previous.items())
    ttl=int(redis('--raw','PTTL','AUTH:RESOURCE_ROLES'));started=time.monotonic()
    try:yield
    finally:
        remaining=ttl-int((time.monotonic()-started)*1000)
        redis('--raw','DEL','AUTH:RESOURCE_ROLES')
        if previous and (ttl<0 or remaining>0):
            for key,value in previous.items():redis('--raw','HSET','AUTH:RESOURCE_ROLES',key,value)
            if ttl>=0:redis('--raw','PEXPIRE','AUTH:RESOURCE_ROLES',str(remaining))
