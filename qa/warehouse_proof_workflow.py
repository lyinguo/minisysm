"""Serial warehouse posting proof and shared stock cost business regression."""
import argparse,datetime,hashlib,json,subprocess,sys,io,zipfile
from acceptance import QA,read_state

MODULES={'store':'psi-j2-storemanagement','sale':'psi-sale','purchase':'psi-j3-purchase','fund':'psi-fund'}
STAGES=[('proof','warehouse_posting_proof_acceptance.py',[],11),
    ('role','stock_role_integration_acceptance.py',[],6),('role-gateway','stock_role_integration_acceptance.py',['--gateway'],6),
    ('entry-baseline','warehouse_acceptance.py',['baseline'],3),('entry-lifecycle','warehouse_acceptance.py',['lifecycle'],8),
    ('sale','sale_posting_acceptance.py',[],7),('purchase-business','purchase_posting_business.py',[],8),
    ('return-cost','sale_return_cost_acceptance.py',['modes'],3),('return-consumed','sale_return_cost_acceptance.py',['consumed'],1),('closed-cost','sale_posting_extended.py',['closed-cost'],1)]

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
    common=QA.parent/'zero-one-12psi/psi-java/psi-common'
    source=common/'src/main/java/com/zeroone/star/project/components/stock/StockCostRebuilder.java'
    classes=common/'target/classes/com/zeroone/star/project/components/stock'
    names=list(classes.glob('StockCostRebuilder*.class'));assert {path.name for path in names}=={'StockCostRebuilder.class','StockCostRebuilder$1.class','StockCostRebuilder$Balance.class','StockCostRebuilder$Layer.class'}
    assert all(path.stat().st_mtime>=source.stat().st_mtime for path in names)
    result['shared_cost_source']=digest(source)
    result['shared_cost_classes']={path.name:digest(path) for path in names}
    for service in ['store','sale','purchase']:
        jar=QA/'runtime/java'/(service+'-project')/'target'/(MODULES[service]+'-1.0.0-SNAPSHOT.jar')
        with zipfile.ZipFile(jar) as app:
            libs=[name for name in app.namelist() if name.startswith('BOOT-INF/lib/psi-common-') and name.endswith('.jar')];assert len(libs)==1
            with zipfile.ZipFile(io.BytesIO(app.read(libs[0]))) as lib:
                for path in names:assert lib.read('com/zeroone/star/project/components/stock/'+path.name)==path.read_bytes(),'Bundled shared cost class mismatch: '+service
    for service,module in [('gateway','psi-gateway'),('login','psi-login')]:
        result[service]=dict(pid=state[service+'_pid'],artifact_sha256=digest(QA/'runtime/java'/(service+'-project')/'target'/(module+'-1.0.0-SNAPSHOT.jar')))
    for name in ['application.yaml','gateway-config/application.yaml','login-config/application.yaml']:
        result[name]=digest(QA/'runtime/java'/name)
    return result

def main(resume=False):
    candidate=snapshot();target=QA/'reports/warehouse-proof-workflow.json'
    report=dict(candidate=candidate,database_isolated=True,production_business_writes=0,all_system_features_accepted=False,all_listed_warehouse_proof_gates_passed=False,stages=[],cases=[],started=datetime.datetime.now().isoformat())
    if resume:
        report=json.loads(target.read_text(encoding='utf-8'));assert report['candidate']==candidate
        recovered=[]
        for index,stage in enumerate(report['stages']):
            name,script,args,count=STAGES[index]
            assert stage==dict(name=name,exit_code=0,verified=count,failed=0)
            archived=json.loads((QA/('reports/warehouse-proof-'+name+'.json')).read_text(encoding='utf-8'))
            assert archived['verified']==count and archived['failed']==0 and archived['database_isolated'] and archived['production_business_writes']==0
            assert all(row['status']=='verified' for row in archived['cases']);recovered.extend(archived['cases'])
        assert recovered==report['cases'];report['resumed']=datetime.datetime.now().isoformat()
        print('RESUME verified '+str(len(recovered))+' archived actual checks',flush=True)
    report['all_listed_warehouse_proof_gates_passed']=False
    for field in ['verified','failed','finished']:report.pop(field,None)
    for name,script,args,count in STAGES[len(report['stages']):]:
        assert snapshot()==candidate,'Candidate changed'
        print('RUN '+name,flush=True)
        result=subprocess.run([sys.executable,'-u',str(QA/script)]+args,cwd=QA.parent)
        current=json.loads((QA/'reports/latest.json').read_text(encoding='utf-8'))
        (QA/('reports/warehouse-proof-'+name+'.json')).write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
        report['stages'].append(dict(name=name,exit_code=result.returncode,verified=current['verified'],failed=current['failed']));report['cases'].extend(current['cases'])
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if result.returncode or current['failed'] or current['verified']!=count:raise SystemExit(result.returncode or 1)
    assert snapshot()==candidate
    total=sum(stage[3] for stage in STAGES)
    assert total==len(report['cases'])==len({row['case'] for row in report['cases']})==54
    assert all(row['status']=='verified' for row in report['cases'])
    report.update(verified=total,failed=0,all_listed_warehouse_proof_gates_passed=True,finished=datetime.datetime.now().isoformat())
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('WAREHOUSE PROOF54 ACTUAL GATES TERMINAL SUCCESS',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');main(parser.parse_args().resume)
