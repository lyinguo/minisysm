"""Serial inbound role, warehouse reference and stock/sales regression."""
import argparse,datetime,hashlib,json,subprocess,sys
from acceptance import QA,read_state

MODULES={'store':'psi-j2-storemanagement','sale':'psi-sale','fund':'psi-fund'}
STAGES=[('role','stock_role_integration_acceptance.py',[],6),
    ('role-gateway','stock_role_integration_acceptance.py',['--gateway'],6),
    ('inbound-baseline','warehouse_acceptance.py',['baseline'],3),
    ('inbound-lifecycle','warehouse_acceptance.py',['lifecycle'],8),
    ('sale-posting','sale_posting_acceptance.py',[],7)]

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot():
    state=read_state();result={}
    for service,module in MODULES.items():
        source=QA.parent/'zero-one-12psi/psi-java'/module/'src'
        mirror=QA/'runtime/java'/(service+'-project');value=hashlib.sha256()
        originals={path.relative_to(source):path for path in source.rglob('*') if path.is_file()}
        copies={path.relative_to(mirror/'src'):path for path in (mirror/'src').rglob('*') if path.is_file()}
        assert originals.keys()==copies.keys()
        for name,path in sorted(originals.items()):
            assert path.read_bytes()==copies[name].read_bytes(),'Source/mirror mismatch: '+service+'/'+str(name)
            value.update(name.as_posix().encode());value.update(path.read_bytes())
        result[service]=dict(source_sha256=value.hexdigest(),artifact_sha256=digest(mirror/'target'/(module+'-1.0.0-SNAPSHOT.jar')),pid=state[service+'_pid'])
    for service,module in [('gateway','psi-gateway'),('login','psi-login')]:
        result[service]=dict(pid=state[service+'_pid'],artifact_sha256=digest(QA/'runtime/java'/(service+'-project')/'target'/(module+'-1.0.0-SNAPSHOT.jar')))
    for name in ['application.yaml','gateway-config/application.yaml','login-config/application.yaml']:
        result[name]=digest(QA/'runtime/java'/name)
    return result

def main(resume=False):
    candidate=snapshot();target=QA/'reports/stock-role-workflow-workflow.json'
    report=dict(candidate=candidate,database_isolated=True,production_business_writes=0,all_system_features_accepted=False,all_listed_inbound_gates_passed=False,stages=[],cases=[],started=datetime.datetime.now().isoformat())
    if resume:
        report=json.loads(target.read_text(encoding='utf-8'));assert report['candidate']==candidate
        recovered=[]
        for index,stage in enumerate(report['stages']):
            name,script,args,count=STAGES[index]
            assert stage==dict(name=name,exit_code=0,verified=count,failed=0)
            archived=json.loads((QA/('reports/stock-role-workflow-'+name+'.json')).read_text(encoding='utf-8'))
            assert archived['verified']==count and archived['failed']==0 and archived['database_isolated'] and archived['production_business_writes']==0
            assert all(row['status']=='verified' for row in archived['cases']);recovered.extend(archived['cases'])
        assert recovered==report['cases'];report['resumed']=datetime.datetime.now().isoformat()
        print('RESUME verified '+str(len(recovered))+' archived actual checks',flush=True)
    for name,script,args,count in STAGES[len(report['stages']):]:
        assert snapshot()==candidate,'Candidate changed'
        print('RUN '+name,flush=True)
        result=subprocess.run([sys.executable,'-u',str(QA/script)]+args,cwd=QA.parent)
        current=json.loads((QA/'reports/latest.json').read_text(encoding='utf-8'))
        (QA/('reports/stock-role-workflow-'+name+'.json')).write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
        report['stages'].append(dict(name=name,exit_code=result.returncode,verified=current['verified'],failed=current['failed']));report['cases'].extend(current['cases'])
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if result.returncode or current['failed'] or current['verified']!=count:raise SystemExit(result.returncode or 1)
    assert snapshot()==candidate
    total=sum(stage[3] for stage in STAGES)
    assert total==len(report['cases'])==len({row['case'] for row in report['cases']})==30
    assert all(row['status']=='verified' for row in report['cases'])
    report.update(verified=total,failed=0,all_listed_inbound_gates_passed=True,finished=datetime.datetime.now().isoformat())
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('STOCK ROLE30 ACTUAL GATES TERMINAL SUCCESS',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');main(parser.parse_args().resume)
