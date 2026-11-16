"""Serial actual procurement role and existing stock/funds/association regression."""
import datetime,hashlib,io,json,subprocess,sys,zipfile,argparse
from acceptance import QA,read_state

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot():
    state=read_state();root=QA.parent/'zero-one-12psi/psi-java/psi-j3-purchase'
    mirror=QA/'runtime/java/purchase-project';value=hashlib.sha256()
    originals={path.relative_to(root/'src'):path for path in (root/'src').rglob('*') if path.is_file()}
    copies={path.relative_to(mirror/'src'):path for path in (mirror/'src').rglob('*') if path.is_file()}
    assert originals.keys()==copies.keys()
    for name,path in sorted(originals.items()):
        assert path.read_bytes()==copies[name].read_bytes(),'Procurement source/mirror differs: '+str(name)
        value.update(name.as_posix().encode());value.update(path.read_bytes())
    name='com/zeroone/star/project/components/user/DatabaseResourcePermission'
    java=root.parent;compiled=java/'psi-common/target/classes'/(name+'.class');source=java/'psi-common/src/main/java'/(name+'.java')
    assert compiled.stat().st_mtime>=source.stat().st_mtime
    jar=mirror/'target/psi-j3-purchase-1.0.0-SNAPSHOT.jar'
    with zipfile.ZipFile(jar) as application:
        libraries=[entry for entry in application.namelist() if entry.startswith('BOOT-INF/lib/psi-common-') and entry.endswith('.jar')]
        assert len(libraries)==1
        with zipfile.ZipFile(io.BytesIO(application.read(libraries[0]))) as library:assert library.read(name+'.class')==compiled.read_bytes()
    value.update(source.read_bytes());value.update(compiled.read_bytes())
    result=dict(source_sha256=value.hexdigest(),artifact_sha256=digest(jar),purchase_pid=state['purchase_pid'])
    for service,module in [('gateway','psi-gateway'),('login','psi-login'),('payment','psi-j6-payment_order')]:
        result[service+'_pid']=state[service+'_pid']
        result[service+'_artifact_sha256']=digest(QA/('runtime/java/'+service+'-project/target/'+module+'-1.0.0-SNAPSHOT.jar'))
    for name in ['application.yaml','gateway-config/application.yaml','login-config/application.yaml']:
        result[name+'_sha256']=digest(QA/'runtime/java'/name)
    return result

def main(resume=False):
    candidate=snapshot()
    stages=[('role','purchase_role_integration_acceptance.py',[],4),('role-gateway','purchase_role_integration_acceptance.py',['--gateway'],4),('order-draft','booking_draft_acceptance.py',['run'],9),('order-audit','booking_audit_acceptance.py',['run'],12),('receive','booking_receive_acceptance.py',['run'],23),('posting','purchase_posting_acceptance.py',['all'],10),('posting-extended','purchase_posting_extended.py',[],11),('security','purchase_security_acceptance.py',[],7),('return-review','purchase_return_review_acceptance.py',['extended'],8),('return-posting','purchase_return_posting_acceptance.py',['extended'],3),('return-scope','purchase_return_posting_acceptance.py',['scope'],1)]
    report=dict(database_isolated=True,production_business_writes=0,all_system_features_accepted=False,all_purchase_role_candidate_gates_passed=False,candidate=candidate,started=datetime.datetime.now().isoformat(),stages=[],cases=[])
    target=QA/'reports/purchase-role-workflow-final.json'
    completed=0
    if resume:
        report=json.loads(target.read_text(encoding='utf-8'))
        assert report['candidate']==candidate,'Cannot resume after a candidate change'
        restored=[]
        for index,stage in enumerate(report['stages']):
            name,script,args,count=stages[index]
            assert stage==dict(name=name,exit_code=0,verified=count,failed=0),'Archived stage does not match corrected manifest'
            archived=json.loads((QA/('reports/purchase-role-workflow-'+name+'.json')).read_text(encoding='utf-8'))
            assert archived['verified']==count and archived['failed']==0 and archived['database_isolated'] and archived['production_business_writes']==0
            assert all(row['status']=='verified' for row in archived['cases'])
            restored.extend(archived['cases'])
        assert report['cases']==restored and len(restored)==len({row['case'] for row in restored})
        completed=len(report['stages']);report['resumed']=datetime.datetime.now().isoformat()
        print('RESUME validated '+str(len(restored))+' actual checks on unchanged candidate',flush=True)
    for name,script,args,count in stages[completed:]:
        assert snapshot()==candidate,'Candidate changed during regression'
        print('RUN '+name,flush=True)
        result=subprocess.run([sys.executable,'-u',str(QA/script)]+args,cwd=QA.parent)
        current=json.loads((QA/'reports/latest.json').read_text(encoding='utf-8'))
        (QA/('reports/purchase-role-workflow-'+name+'.json')).write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
        report['stages'].append(dict(name=name,exit_code=result.returncode,verified=current['verified'],failed=current['failed']));report['cases'].extend(current['cases'])
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if result.returncode or current['failed'] or current['verified']!=count:raise SystemExit(result.returncode or 1)
    assert snapshot()==candidate
    assert len(report['cases'])==len({row['case'] for row in report['cases']})==92
    assert all(row['status']=='verified' for row in report['cases'])
    report.update(verified=92,failed=0,all_purchase_role_candidate_gates_passed=True,finished=datetime.datetime.now().isoformat())
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PURCHASE ROLE92 ACTUAL GATES TERMINAL SUCCESS',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');main(parser.parse_args().resume)
