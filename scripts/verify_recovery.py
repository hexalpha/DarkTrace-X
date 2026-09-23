import json,subprocess,time
import os
import shlex
from pathlib import Path
import httpx
root=Path(__file__).resolve().parents[1]
def docker(*args):
    options=shlex.split(os.environ.get('DARKTRACE_COMPOSE_OPTIONS',''))
    return subprocess.run(['docker','compose',*options,*args],cwd=root,capture_output=True,text=True,check=True).stdout

def ready(path='/api/v1/health/ready',seconds=100):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        try:
            if httpx.get('http://localhost:8080'+path,timeout=3).status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(1)
    raise RuntimeError('Recovery deadline exceeded: '+path)

active=docker('exec','-T','postgres','psql','-U','darktrace','-d','darktracex','-Atc',"SELECT count(*) FROM source_crawl_jobs WHERE status='running';").strip()
if active!='0':raise RuntimeError('Active crawls exist; restart tests postponed')
fingerprint_sql="SELECT count(*),md5(string_agg(content_hash,',' ORDER BY content_hash)) FROM source_documents;"
before=docker('exec','-T','postgres','psql','-U','darktrace','-d','darktracex','-Atc',fingerprint_sql).strip()
results={}
for service in ('redis','postgres','elasticsearch'):
    started=time.monotonic()
    docker('stop',service)
    try:
        if service=='redis':
            response=httpx.post('http://localhost:8080/api/v1/auth/login',json={'tenant_id':'recovery-no-account','email':'qa@example.com','password':'invalid'},timeout=10)
        else:
            response=httpx.get('http://localhost:8080/api/v1/health/ready',timeout=10)
        assert response.status_code==503,(service,response.status_code)
    finally:
        docker('start',service)
    ready()
    if service=='redis':
        response=httpx.post('http://localhost:8080/api/v1/auth/login',json={'tenant_id':'recovery-no-account','email':'qa@example.com','password':'invalid'},timeout=10)
        assert response.status_code==401,response.status_code
    results[service]={'failure_detected':True,'recovered':True,'elapsed_seconds':round(time.monotonic()-started,2)}
    print('PASS',service,'failure detection and recovery',flush=True)
for service,path in (('api','/api/v1/health/ready'),('web','/')):
    docker('restart',service);ready(path)
    results[service]={'recovered':True}
    print('PASS',service,'restart recovery',flush=True)
after=docker('exec','-T','postgres','psql','-U','darktrace','-d','darktracex','-Atc',fingerprint_sql).strip()
assert before==after,'Document integrity changed'
results['document_integrity_preserved']=True
print(json.dumps(results,indent=2),flush=True)
