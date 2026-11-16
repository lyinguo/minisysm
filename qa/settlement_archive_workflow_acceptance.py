"""Serial archive-boundary and existing real posting/rollback regression gates."""
import datetime
import json
import subprocess
import sys
from acceptance import QA, read_state
from receipt_workflow_acceptance import digest, source_digest as receipt_sources
from payment_workflow_acceptance import source_digest as payment_sources


def snapshot():
    state = read_state()
    fund = QA / 'runtime/java/fund-project/target/psi-fund-1.0.0-SNAPSHOT.jar'
    payment = QA / 'runtime/java/payment-project/target/psi-j6-payment_order-1.0.0-SNAPSHOT.jar'
    return dict(fund_pid=state['fund_pid'], payment_pid=state['payment_pid'],
                fund_sha256=digest(fund), payment_sha256=digest(payment),
                fund_source_sha256=receipt_sources(fund), payment_source_sha256=payment_sources())


def main():
    candidate = snapshot()
    stages = [('archive', 'settlement_archive_acceptance.py', [], 4),
              ('payment-preview', 'payment_settlement_acceptance.py', [], 3),
              ('payment-posting', 'payment_settlement_posting_acceptance.py', [], 5),
              ('payment-credit', 'payment_settlement_posting_acceptance.py', ['residual'], 1),
              ('receipt-posting', 'receipt_settlement_acceptance.py', [], 7)]
    report = dict(database_isolated=True, production_business_writes=0,
                  all_system_features_accepted=False, candidate=candidate,
                  started=datetime.datetime.now().isoformat(), stages=[], cases=[])
    target = QA / 'reports/settlement-archive-workflow-final.json'
    for name, script, arguments, count in stages:
        assert snapshot() == candidate, 'Candidate changed during regression'
        print('RUN ' + name, flush=True)
        result = subprocess.run([sys.executable, '-u', str(QA / script)] + arguments, cwd=QA.parent)
        current = json.loads((QA / 'reports/latest.json').read_text(encoding='utf-8'))
        (QA / 'reports/settlement-archive-workflow-{}.json'.format(name)).write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding='utf-8')
        report['stages'].append(dict(name=name, exit_code=result.returncode, verified=current['verified'], failed=current['failed']))
        report['cases'].extend(current['cases'])
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        if result.returncode or current['failed'] or current['verified'] != count:
            raise SystemExit(result.returncode or 1)
    assert snapshot() == candidate, 'Final candidate changed'
    assert len(report['cases']) == len({row['case'] for row in report['cases']}) == 20
    assert all(row['status'] == 'verified' for row in report['cases'])
    report.update(verified=20, failed=0, finished=datetime.datetime.now().isoformat())
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('SETTLEMENT ARCHIVE20 REAL GATES TERMINAL SUCCESS', flush=True)


if __name__ == '__main__':
    main()
