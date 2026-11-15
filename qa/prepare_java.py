"""Prepare private isolated Java configuration; never print configuration values."""
import json
import re
import secrets
from pathlib import Path
import yaml
from acceptance import ROOT, QA, read_state


def merge(target, source):
    for key, value in source.items():
        if isinstance(value, dict):
            merge(target.setdefault(key, {}), value)
        else:
            target[key] = value


def main():
    state = read_state()
    configuration = {}
    for name in ['system', 'data-source', 'third-services', 'key-config']:
        merge(configuration, yaml.safe_load((ROOT / 'nacos-local' / (name + '.yaml')).read_text(encoding='utf-8-sig')))
    datasource = configuration['spring']['datasource']
    jdbc = datasource['url']
    jdbc, replaced = re.subn(r'(jdbc:mysql://[^/]+/)[^?]+', lambda match: match[1] + state['database'], jdbc)
    if replaced != 1:
        raise RuntimeError('Unrecognized database URL; refusing to start')
    datasource['url'] = jdbc
    # Some modules bind spring.datasource.druid directly; root-only overrides
    # would leave their embedded datasource pointed at the normal database.
    datasource['druid'] = {key: datasource[key] for key in ['url', 'username', 'password', 'driver-class-name'] if key in datasource}
    configuration['spring']['redis'] = {'host': '127.0.0.1', 'port': 18379, 'database': 0}
    configuration['server'] = {'port': 18002}
    configuration['spring']['application'] = {'name': 'QA-OAUTH2'}
    configuration['spring']['profiles'] = {'active': 'qa'}
    client = {'mgr-id': 'qa-manager', 'mgr-password': secrets.token_urlsafe(24)}
    merge(configuration, {'zo': {'cloud': {'starter': {'oauth2': client}}}})
    merge(configuration, {'spring': {'cloud': {
        'nacos': {'discovery': {'enabled': False, 'register-enabled': False}, 'config': {'enabled': False}},
        'discovery': {'enabled': False}, 'sentinel': {'enabled': False}}}})
    destination = QA / 'runtime/java'
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'application.yaml').write_text(yaml.safe_dump(configuration, allow_unicode=True), encoding='utf-8')
    (QA / 'runtime/oauth-client.json').write_text(json.dumps(client), encoding='utf-8')
    state['oauth_port'] = 18002
    (QA / '.state.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    print('Private Java configuration prepared: isolated MySQL, Redis and OAuth port; discovery disabled.')


if __name__ == '__main__':
    main()
