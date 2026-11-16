"""Generate isolated real Login->OAuth config, including actual token registration."""
import yaml,re
from acceptance import QA,read_state
state=read_state()
assert state['oauth_port']==18002
configuration=yaml.safe_load((QA/'runtime/java/application.yaml').read_text(encoding='utf-8-sig'))
assert configuration['spring']['redis']['port']==18379
urls=re.findall(r'jdbc:mysql://[^\s\'\"]+',yaml.safe_dump(configuration))
assert len(urls)>=2 and all('/'+state['database']+'?' in url for url in urls),'All Login datasources must be isolated'
configuration['server']=dict(port=18003,address='127.0.0.1')
configuration.setdefault('sn',{})['auth']='QA-OAUTH2'
configuration['QA-OAUTH2']=dict(ribbon=dict(listOfServers='127.0.0.1:18002',NFLoadBalancerRuleClassName='com.netflix.loadbalancer.RoundRobinRule',NFLoadBalancerPingClassName='com.netflix.loadbalancer.DummyPing'))
configuration.setdefault('ribbon',{}).setdefault('eureka',{})['enabled']=False
configuration.setdefault('zo',{}).setdefault('captcha',{})['enabled']=False
directory=QA/'runtime/java/login-config';directory.mkdir(exist_ok=True)
(directory/'application.yaml').write_text(yaml.safe_dump(configuration,allow_unicode=True,sort_keys=False),encoding='utf-8')
print('Private Login config generated: port18003, actual QA OAuth18002, QA Redis18379; CAPTCHA disabled for this auth fixture')
