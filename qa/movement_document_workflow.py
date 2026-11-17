"""Freeze the actual outbound candidate and run all affected real business gates serially."""
import argparse,datetime,hashlib,io,json,subprocess,sys,zipfile
from acceptance import QA
from warehouse_proof_workflow import snapshot as services
from warehouse_cost_workflow import STAGES as PREVIOUS

from outbound_document_workflow import STAGES as PREVIOUS_OUTBOUND
STAGES=PREVIOUS_OUTBOUND+[('movement-direct','movement_document_acceptance.py',[],21),('movement-gateway','movement_document_acceptance.py',['--gateway'],21)]

def snapshot():
    result=services();root=QA.parent/'zero-one-12psi'
    result['outbound_frontend']={name:hashlib.sha256((root/'psi-frontend/src'/name).read_bytes()).hexdigest() for name in ['views/warehouse/outbound/OtherOutbound.vue','components/warehouse/WarehouseDocumentReport.vue','components/warehouse/MovementWorkspace.vue','views/warehouse/transfer/TransferOrder.vue','views/warehouse/check/Index.vue']}
    with zipfile.ZipFile(QA/'runtime/java/store-project/target/psi-j2-storemanagement-1.0.0-SNAPSHOT.jar') as app:
        for module,classes in [('psi-domain',['dto/j2/store/OtherOutListDTO.class']),('psi-apis',['j2/store/OtherOutApis.class'])]:
            libs=[name for name in app.namelist() if name.startswith('BOOT-INF/lib/'+module+'-') and name.endswith('.jar')];assert len(libs)==1
            source=root/'psi-java'/module/'src/main/java/com/zeroone/star/project';built=root/'psi-java'/module/'target/classes/com/zeroone/star/project'
            with zipfile.ZipFile(io.BytesIO(app.read(libs[0]))) as lib:
                for name in classes:
                    path=built/name;assert path.stat().st_mtime>=source.joinpath(name.replace('.class','.java')).stat().st_mtime
                    assert lib.read('com/zeroone/star/project/'+name)==path.read_bytes(),'Bundled outbound dependency differs from compiled current source'
                    result[module+'/'+name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result

def main(resume=False):
    candidate=snapshot();report=dict(candidate=candidate,database_isolated=True,production_business_writes=0,all_system_features_accepted=False,stages=[],cases=[],started=datetime.datetime.now().isoformat());target=QA/'reports/movement-document-workflow.json'
    if resume:
        report=json.loads(target.read_text(encoding='utf-8'));assert report['candidate']==candidate
        cases=[]
        for index,stage in enumerate(report['stages']):
            name,script,args,count=STAGES[index];assert stage==dict(name=name,exit_code=0,verified=count,failed=0)
            archived=json.loads((QA/('reports/movement-workflow-'+name+'.json')).read_text(encoding='utf-8'));assert archived['verified']==count and archived['failed']==0 and archived['database_isolated'] and archived['production_business_writes']==0
            assert all(case['status']=='verified' for case in archived['cases']);cases.extend(archived['cases'])
        assert cases==report['cases'];print('RESUME '+str(len(cases))+' actual archived checks on unchanged candidate',flush=True)
    report['all_listed_gates_passed']=False
    for key in ['verified','failed','finished']:report.pop(key,None)
    for name,script,args,count in STAGES[len(report['stages']):]:
        assert snapshot()==candidate,'Candidate changed during actual business checks'
        print('RUN '+name,flush=True);process=subprocess.run([sys.executable,'-u',str(QA/script)]+args,cwd=QA.parent)
        current=json.loads((QA/'reports/latest.json').read_text(encoding='utf-8'));(QA/('reports/movement-workflow-'+name+'.json')).write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
        report['stages'].append(dict(name=name,exit_code=process.returncode,verified=current['verified'],failed=current['failed']));report['cases'].extend(current['cases']);target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if process.returncode or current['failed'] or current['verified']!=count:raise SystemExit(process.returncode or 1)
    assert snapshot()==candidate
    assert sum(stage[3] for stage in STAGES)==199==len(report['cases'])==len({case['case'] for case in report['cases']})
    report.update(verified=199,failed=0,all_listed_gates_passed=True,finished=datetime.datetime.now().isoformat());target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('MOVEMENT199 ACTUAL BUSINESS GATES TERMINAL SUCCESS',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');main(p.parse_args().resume)
