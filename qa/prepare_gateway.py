"""Generate a private QA gateway config with only explicitly isolated routes."""
import yaml,re
from acceptance import QA, read_state

state = read_state()
assert state['c1_port'] == 18091 and state['payment_port'] == 18024 and state['fund_port'] == 18026 and state['purchase_port']==18023
configuration = yaml.safe_load((QA / 'runtime/java/application.yaml').read_text(encoding='utf-8-sig'))
urls=re.findall(r'jdbc:mysql://[^\s\'\"]+',yaml.safe_dump(configuration))
assert len(urls)>=2 and all('/'+state['database']+'?' in url for url in urls),'All gateway datasources must be isolated'
spring = configuration['spring']
assert spring['redis']['port'] == 18379
spring.setdefault('main', {})['web-application-type'] = 'reactive'
cloud = spring.setdefault('cloud', {})
cloud['gateway'] = dict(discovery=dict(locator=dict(enabled=False)), routes=[
    dict(id='qa-payment', uri='http://127.0.0.1:18024', predicates=['Path=/payment-order/**']),
    dict(id='qa-receipt', uri='http://127.0.0.1:18026', predicates=['Path=/fund/receipt/**']),
    dict(id='qa-login', uri='http://127.0.0.1:18003', predicates=['Path=/login/**']),
    dict(id='qa-purchase', uri='http://127.0.0.1:18023', predicates=['Path=/j3-purchase/**'], filters=['StripPrefix=1']),
    dict(id='qa-identity', uri='http://127.0.0.1:18091', predicates=['Path=/role/**,/user/**'])])
configuration['server'] = dict(port=18001, address='127.0.0.1')
configuration.setdefault('management', {}).setdefault('endpoints', {}).setdefault('web', {}).setdefault('exposure', {})['include'] = 'health,gateway'
configuration.setdefault('zo', {}).setdefault('cloud', {}).setdefault('gateway', {})['open-authorization'] = False
# This is the application's existing policy: JWT authentication at the gateway,
# committed function/organization authorization in the actual business services.
directory = QA / 'runtime/java/gateway-config'
directory.mkdir(exist_ok=True)
(directory / 'application.yaml').write_text(yaml.safe_dump(configuration, allow_unicode=True, sort_keys=False), encoding='utf-8')
print('Private gateway config generated: only QA identity/login/payment/receipt/procurement routes, QA Redis18379, port18001')
