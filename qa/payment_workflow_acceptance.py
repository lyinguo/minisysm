"""Serial actual finance acceptance; component tests are reported separately."""
import hashlib,json,subprocess,sys,datetime,io,zipfile
from pathlib import Path
from acceptance import QA,read_state

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def source_digest():
    root=QA.parent/'zero-one-12psi/psi-java/psi-j6-payment_order/src/main/java'
    mirror=QA/'runtime/java/payment-project/src/main/java'
    value=hashlib.sha256()
    for path in sorted(root.rglob('*.java')):
        relative=path.relative_to(root);assert (mirror/relative).read_bytes()==path.read_bytes(),'QA source mirror differs: '+str(relative)
        value.update(str(relative).encode());value.update(path.read_bytes())
    java=QA.parent/'zero-one-12psi/psi-java'
    name='com/zeroone/star/project/components/user/DatabaseResourcePermission'
    source=java/'psi-common/src/main/java'/(name+'.java')
    compiled=java/'psi-common/target/classes'/(name+'.class')
    assert compiled.stat().st_mtime>=source.stat().st_mtime,'Permission source changed after compilation'
    with zipfile.ZipFile(QA/'runtime/java/payment-project/target/psi-j6-payment_order-1.0.0-SNAPSHOT.jar') as application:
        libraries=[entry for entry in application.namelist() if entry.startswith('BOOT-INF/lib/psi-common-') and entry.endswith('.jar')]
        assert len(libraries)==1
        with zipfile.ZipFile(io.BytesIO(application.read(libraries[0]))) as library:
            assert library.read(name+'.class')==compiled.read_bytes(),'Bundled committed-role evaluator differs from compiled source'
    value.update(source.read_bytes());value.update(compiled.read_bytes())
    return value.hexdigest()

def main():
    state=read_state();assert state['payment_port']==18024
    jar=QA/'runtime/java/payment-project/target/psi-j6-payment_order-1.0.0-SNAPSHOT.jar'
    artifact=digest(jar);sources=source_digest();process=state['payment_pid']
    gateway_jar=QA/'runtime/java/gateway-project/target/psi-gateway-1.0.0-SNAPSHOT.jar'
    gateway_config=QA/'runtime/java/gateway-config/application.yaml'
    login_jar=QA/'runtime/java/login-project/target/psi-login-1.0.0-SNAPSHOT.jar'
    login_config=QA/'runtime/java/login-config/application.yaml'
    gateway=dict(pid=state['gateway_pid'],artifact_sha256=digest(gateway_jar),config_sha256=digest(gateway_config),login_pid=state['login_pid'],login_artifact_sha256=digest(login_jar),login_config_sha256=digest(login_config))
    def assert_gateway():
        assert read_state()['gateway_pid']==gateway['pid'] and digest(gateway_jar)==gateway['artifact_sha256'] and digest(gateway_config)==gateway['config_sha256'],'QA gateway changed during regression'
        assert read_state()['login_pid']==gateway['login_pid'] and digest(login_jar)==gateway['login_artifact_sha256'] and digest(login_config)==gateway['login_config_sha256'],'QA Login changed during regression'
    stages=[('role','payment_role_integration_acceptance.py',[]),('role-gateway','payment_role_integration_acceptance.py',['--gateway']),('draft','payment_draft_acceptance.py',[]),('preview','payment_settlement_acceptance.py',[]),('posting','payment_settlement_posting_acceptance.py',[]),('residual','payment_settlement_posting_acceptance.py',['residual']),('document','payment_document_acceptance.py',[]),('scope','payment_document_scope_acceptance.py',[]),('import','payment_import_acceptance.py',[]),('export','payment_export_acceptance.py',[]),('options','payment_options_acceptance.py',[]),('boundary','payment_settlement_boundary_acceptance.py',[]),('identity','payment_identity_acceptance.py',[]),('competing','payment_competing_settlement_acceptance.py',[])]
    report=dict(database_isolated=True,production_business_writes=0,all_system_features_accepted=False,all_payment_candidate_gates_passed=False,payment_pid=process,artifact_sha256=artifact,source_sha256=sources,gateway=gateway,started=datetime.datetime.now().isoformat(),stages=[],cases=[])
    target=QA/'reports/payment-workflow-final.json'
    for name,script,arguments in stages:
        assert read_state()['payment_pid']==process and digest(jar)==artifact and source_digest()==sources,'Candidate changed during regression'
        assert_gateway()
        print('RUN '+name,flush=True)
        result=subprocess.run([sys.executable,'-u',str(QA/script)]+arguments,cwd=QA.parent)
        current=json.loads((QA/'reports/latest.json').read_text(encoding='utf-8'))
        (QA/'reports'/('payment-workflow-final-'+name+'.json')).write_text(json.dumps(current,ensure_ascii=False,indent=2),encoding='utf-8')
        assert current['database_isolated'] and current['production_business_writes']==0
        report['stages'].append(dict(name=name,exit_code=result.returncode,verified=current['verified'],failed=current['failed']))
        report['cases'].extend(current['cases']);target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        if result.returncode or current['failed']:raise SystemExit(result.returncode or 1)
    assert read_state()['payment_pid']==process and digest(jar)==artifact and source_digest()==sources,'Final candidate changed'
    assert_gateway()
    identifiers=[row['case'] for row in report['cases']]
    assert len(identifiers)==len(set(identifiers))==50,'Unexpected duplicate or missing actual payment gates'
    assert all(row['status']=='verified' for row in report['cases'])
    report.update(all_payment_candidate_gates_passed=True,verified=50,failed=0,finished=datetime.datetime.now().isoformat())
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PAYMENT WORKFLOW50 ACTUAL GATES TERMINAL SUCCESS',flush=True)

if __name__=='__main__':main()
