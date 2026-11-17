"""Serial business verification for exact warehouse costs and all affected callers."""
import argparse,datetime,json,subprocess,sys
from acceptance import QA
from warehouse_proof_workflow import snapshot,STAGES as PREVIOUS
STAGES=[('issue-transfer','warehouse_cost_flow_acceptance.py',[],10),('cost-scopes','warehouse_cost_flow_acceptance.py',['--matrix'],24)]+PREVIOUS+[('inbound-files','inbound_file_acceptance.py',[],18),('serial-mixed','warehouse_cost_flow_acceptance.py',['--mixed-serial'],1),('serial-return','warehouse_cost_flow_acceptance.py',['--serial-return'],1),('serial-return-resale','warehouse_cost_flow_acceptance.py',['--serial-return-both'],1),('return-variants','sale_return_posting_acceptance.py',['variants'],4),('return-edges','sale_return_posting_acceptance.py',['edges'],4)]

def main(resume=False):
    candidate=snapshot();target=QA/'reports/warehouse-cost-workflow.json'
    report=dict(candidate=candidate,database_isolated=True,production_business_writes=0,all_system_features_accepted=False,all_listed_cost_gates_passed=False,stages=[],cases=[],started=datetime.datetime.now().isoformat())
    if resume:
        report=json.loads(target.read_text(encoding='utf-8'));assert report['candidate']==candidate,'Candidate changed since archived actual tests'
        recovered=[]
        for index,stage in enumerate(report['stages']):
            name,script,args,count=STAGES[index];assert stage==dict(name=name,exit_code=0,verified=count,failed=0)
            archived=json.loads((QA/('reports/warehouse-cost-workflow-'+name+'.json')).read_text(encoding='utf-8'))
            assert archived['verified']==count and archived['failed']==0 and archived['database_isolated'] and archived['production_business_writes']==0 and not archived['all_system_features_accepted']
            assert all(row['status']=='verified' for row in archived['cases']);recovered.extend(archived['cases'])
        assert recovered==report['cases'];report['resumed']=datetime.datetime.now().isoformat();print('RESUME verified '+str(len(recovered))+' archived actual checks',flush=True)
    report['all_listed_cost_gates_passed']=False
    for field in ['verified','failed','finished']:report.pop(field,None)
    for name,script,args,count in STAGES[len(report['stages']):]:
        assert snapshot()==candidate,'Source/artifact/configuration/PID changed during actual workflow'
        print('RUN '+name,flush=True)
        result=subprocess.run([sys.executable,'-u',str(QA/script)]+args,cwd=QA.parent)
        current=json.loads((QA/'reports/latest.json').read_text(encoding='utf-8'))
        (QA/('reports/warehouse-cost-workflow-'+name+'.json')).write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
        report['stages'].append(dict(name=name,exit_code=result.returncode,verified=current['verified'],failed=current['failed']));report['cases'].extend(current['cases'])
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if result.returncode or current['failed'] or current['verified']!=count:raise SystemExit(result.returncode or 1)
    assert snapshot()==candidate
    total=sum(stage[3] for stage in STAGES);assert total==117==len(report['cases'])==len({row['case'] for row in report['cases']})
    assert all(row['status']=='verified' for row in report['cases'])
    report.update(verified=total,failed=0,all_listed_cost_gates_passed=True,finished=datetime.datetime.now().isoformat());target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('WAREHOUSE COST117 ACTUAL GATES TERMINAL SUCCESS',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');main(p.parse_args().resume)
