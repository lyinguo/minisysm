"""Serial real receipt gates; browser and component verification stay separate."""
import datetime,hashlib,io,json,subprocess,sys,zipfile
from acceptance import QA,read_state

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def source_digest(jar):
    root=QA.parent/'zero-one-12psi/psi-java';source=root/'psi-fund';mirror=QA/'runtime/java/fund-project'
    originals={path.relative_to(source/'src'):path for path in (source/'src').rglob('*') if path.is_file()}
    copies={path.relative_to(mirror/'src'):path for path in (mirror/'src').rglob('*') if path.is_file()}
    assert originals.keys()==copies.keys(),'QA source mirror has missing or obsolete files'
    value=hashlib.sha256()
    for name,path in sorted(originals.items()):
        assert path.read_bytes()==copies[name].read_bytes(),'QA source mirror differs: '+str(name)
        value.update(name.as_posix().encode());value.update(path.read_bytes())
    value.update((source/'pom.xml').read_bytes());value.update((mirror/'pom.xml').read_bytes())
    critical=[('psi-common','com/zeroone/star/project/components/user/DatabaseResourcePermission'),('psi-apis','com/zeroone/star/project/j4/FundReceiptFormApis'),('psi-domain','com/zeroone/star/project/dto/j4/fund/ReceiptAddDTO'),('psi-domain','com/zeroone/star/project/dto/j4/fund/ReceiptSettlementDetailDTO')]
    with zipfile.ZipFile(jar) as application:
        for module,name in critical:
            source_file=root/module/'src/main/java'/(name+'.java');compiled=root/module/'target/classes'/(name+'.class')
            assert compiled.stat().st_mtime>=source_file.stat().st_mtime,'Shared source changed after compilation: '+name
            libraries=[entry for entry in application.namelist() if entry.startswith('BOOT-INF/lib/'+module+'-') and entry.endswith('.jar')]
            assert len(libraries)==1,'Expected one bundled shared module: '+module
            with zipfile.ZipFile(io.BytesIO(application.read(libraries[0]))) as library:
                assert library.read(name+'.class')==compiled.read_bytes(),'Bundled shared authorization/API/DTO class differs: '+name
            value.update(source_file.read_bytes());value.update(compiled.read_bytes())
    return value.hexdigest()

def main():
    state=read_state();assert state['fund_port']==18026
    jar=QA/'runtime/java/fund-project/target/psi-fund-1.0.0-SNAPSHOT.jar'
    artifact=digest(jar);sources=source_digest(jar);process=state['fund_pid']
    stages=[('draft','receipt_draft_acceptance.py',[],8),('document','receipt_document_acceptance.py',[],5),('scope','receipt_document_scope_acceptance.py',[],4),('trade','receipt_trade_acceptance.py',['settle'],1),('posting','receipt_settlement_acceptance.py',[],7),('role','receipt_role_integration_acceptance.py',[],1),('import','receipt_import_acceptance.py',[],8),('export','receipt_export_acceptance.py',[],3),('legacy-file','receipt_import_legacy_acceptance.py',[],2),('file','receipt_file_import_acceptance.py',[],7)]
    report=dict(database_isolated=True,production_business_writes=0,all_system_features_accepted=False,all_receipt_candidate_gates_passed=False,receipt_pid=process,artifact_sha256=artifact,source_sha256=sources,started=datetime.datetime.now().isoformat(),stages=[],cases=[])
    target=QA/'reports/receipt-workflow-final.json'
    for name,script,args,expected in stages:
        assert read_state()['fund_pid']==process and digest(jar)==artifact and source_digest(jar)==sources,'Candidate changed during regression'
        print('RUN '+name,flush=True);result=subprocess.run([sys.executable,'-u',str(QA/script)]+args,cwd=QA.parent)
        current=json.loads((QA/'reports/latest.json').read_text(encoding='utf-8'))
        (QA/'reports'/('receipt-workflow-final-'+name+'.json')).write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
        assert current['database_isolated'] and current['production_business_writes']==0
        report['stages'].append(dict(name=name,exit_code=result.returncode,verified=current['verified'],failed=current['failed']));report['cases'].extend(current['cases'])
        target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if result.returncode or current['failed'] or current['verified']!=expected:raise SystemExit(result.returncode or 1)
    assert read_state()['fund_pid']==process and digest(jar)==artifact and source_digest(jar)==sources,'Final receipt candidate changed'
    identifiers=[row['case'] for row in report['cases']];assert len(identifiers)==len(set(identifiers))==46
    assert all(row['status']=='verified' for row in report['cases'])
    report.update(all_receipt_candidate_gates_passed=True,verified=46,failed=0,finished=datetime.datetime.now().isoformat())
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('RECEIPT WORKFLOW46 ACTUAL GATES TERMINAL SUCCESS',flush=True)

if __name__=='__main__':main()
