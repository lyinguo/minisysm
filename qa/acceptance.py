"""Actual HTTP + isolated MySQL acceptance. Never write business APIs on production ports."""
import argparse
import datetime
import importlib.util
import json
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
import uuid
import concurrent.futures
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'qa'
STATE = QA / '.state.json'
spec = importlib.util.spec_from_file_location('master_integrity', ROOT / 'scripts/lib/master-integrity.py')
integrity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(integrity)


def literal(value):
    if value is None:
        return 'NULL'
    text = str(value)
    return "''" if not text else 'CONVERT(0x' + text.encode('utf-8').hex() + ' USING utf8mb4)'


def authenticate():
    config = {}
    local = QA / 'runtime/credentials.json'
    if local.exists():
        config = json.loads(local.read_text(encoding='utf-8-sig'))
    username = os.environ.get('PSI_USERNAME') or config.get('username')
    credential = os.environ.get('PSI_PASSWORD') or config.get('password')
    if not username or not credential:
        raise RuntimeError('Set PSI_USERNAME/PSI_PASSWORD locally; no credentials are bundled.')
    request = urllib.request.Request('http://127.0.0.1:10001/login/auth-login',
                                     data=urllib.parse.urlencode({'username': username, 'password': credential}).encode())
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=20) as response:
        body = json.load(response)
    if body.get('code') != 10000 or not isinstance(body.get('data'), dict):
        raise RuntimeError('Acceptance authentication failed')
    token = body['data']['token']
    import base64
    payload = token.split('.')[1]
    claims = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))
    return opener, token, claims


def read_state():
    state = json.loads(STATE.read_text(encoding='utf-8-sig'))
    if not re.fullmatch(r'psi_qa_[0-9a-f]{12}', state['database']):
        raise RuntimeError('Refusing a non-QA database')
    return state


def authenticate_isolated(state):
    """Bootstrap a fresh disposable QA administrator and obtain a real QA token.

    Never reuse a normal-environment identity to exercise privileged QA writes.
    The reserved role0 is an explicit setup fixture, not an account API feature.
    """
    import bcrypt
    if not re.fullmatch(r'psi_qa_[0-9a-f]{12}',state['database']) or state.get('oauth_port')!=18002:
        raise RuntimeError('Refusing administrator setup outside isolated QA')
    identifier=uuid.uuid4().hex;login='qa_admin_'+identifier[:16];credential=secrets.token_urlsafe(18)
    hashed=bcrypt.hashpw(credential.encode(),bcrypt.gensalt()).decode()
    fields=['id','name','py','tel','frame','role','user','pwd','img','token','expire','data','more']
    values=[identifier,'QA Isolated Administrator','qa','199'+str(int(identifier[:8],16)%100000000).zfill(8),state['frame_id'],'0',login,hashed,'','',0,'Explicit isolated administrator fixture','{}']
    sql(state,'INSERT INTO `user`('+','.join('`'+key+'`' for key in fields)+') VALUES('+','.join(literal(value) for value in values)+');')
    client=json.loads((QA/'runtime/oauth-client.json').read_text(encoding='utf-8'))
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request=urllib.request.Request('http://127.0.0.1:18002/oauth/token',data=urllib.parse.urlencode(dict(grant_type='password',client_id=client['mgr-id'],client_secret=client['mgr-password'],username=login,password=credential)).encode())
    with opener.open(request,timeout=20) as response:body=json.load(response)
    token=body.get('access_token') or body.get('token')
    if not token:raise RuntimeError('Fresh isolated administrator could not authenticate')
    import base64
    payload=token.split('.')[1]
    claims=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))
    if claims.get('id')!=identifier:raise RuntimeError('QA authentication returned a different identity')
    return opener,token,claims


def sql(state, statement):
    if not re.fullmatch(r'psi_qa_[0-9a-f]{12}', state['database']):
        raise RuntimeError('Refusing a non-QA database')
    return integrity.query(state['container'], state['database'], statement).stdout.strip()


def bootstrap():
    if STATE.exists():
        print('Existing isolated environment retained; inspect qa/.state.json before replacing it.')
        return
    _, _, actor = authenticate()
    state = {'database': 'psi_qa_' + uuid.uuid4().hex[:12], 'container': 'mysql8',
             'created': datetime.datetime.utcnow().isoformat() + 'Z',
             'actor_id': str(actor['id']), 'actor_login': str(actor.get('user_name', 'admin')),
             'frame_id': uuid.uuid4().hex, 'role_id': uuid.uuid4().hex,
             'c1_port': 18091}
    integrity.query(state['container'], None, 'CREATE DATABASE `' + state['database'] + '` CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci;')
    schema_path = ROOT / 'database/schema.sql'
    if not schema_path.exists():
        schema_path = ROOT / '.publication/database/schema.sql'
    schema = schema_path.read_text(encoding='utf-8')
    sql(state, schema)
    sql(state, (ROOT / 'database/migrations/20261115_sale_rate_precision.sql').read_text(encoding='utf-8'))
    sql(state, (ROOT / 'database/migrations/20261115_sale_posting.sql').read_text(encoding='utf-8'))
    integrity.install(state['container'], state['database'])
    sql(state, "INSERT INTO frame(id,pid,name,sort,data) VALUES(" + literal(state['frame_id']) + ",'0','QA Organization',0,'');")
    sql(state, "INSERT INTO role(id,name,data,root,auth,keyword) VALUES(" + literal(state['role_id']) + ",'QA Role','','{}','{}','');")
    fields = ['id', 'name', 'py', 'tel', 'frame', 'role', 'user', 'pwd', 'img', 'token', 'expire', 'data', 'more']
    values = [state['actor_id'], 'QA Actor', 'qa', '19900000000', state['frame_id'], state['role_id'],
              state['actor_login'], 'QA_DISABLED_LOGIN', '', '', 0, '', '{}']
    sql(state, 'INSERT INTO `user`(' + ','.join('`' + key + '`' for key in fields) + ') VALUES(' + ','.join(literal(value) for value in values) + ');')
    QA.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2), encoding='utf-8')
    print('Isolated database created: ' + state['database'] + '; business data copied: 0')


class Suite:
    def __init__(self, state):
        self.state = state
        self.opener, self.token, _ = authenticate_isolated(state)
        self.results = []

    def request(self, method, path, body=None, service='c1'):
        port = self.state[service + '_port']
        dedicated_ports = {'c1': 18091, 'supportinfo': 18007, 'store': 18020, 'basic': 18021, 'sale': 18022, 'purchase': 18023, 'payment': 18024, 'homepage': 18025, 'fund': 18026}
        if dedicated_ports.get(service) != port or not path.startswith('/'):
            raise RuntimeError('Refusing writes outside isolated service ports')
        request = urllib.request.Request('http://127.0.0.1:' + str(port) + path, method=method,
                                        data=None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8'),
                                        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.token})
        try:
            with self.opener.open(request, timeout=20) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            raise AssertionError('HTTP ' + str(error.code) + ' at ' + path.split('?')[0])

    def success(self, method, path, body=None):
        result = self.request(method, path, body)
        assert result.get('code') == 10000, 'Expected success at ' + path.split('?')[0] + '; code=' + str(result.get('code'))
        return result.get('data')

    def case(self, name, action):
        try:
            assertions = action()
            result = {'case': name, 'status': 'verified', 'evidence': assertions}
        except Exception as error:
            result = {'case': name, 'status': 'failed', 'reason': str(error)}
        self.results.append(result)
        print(result['status'].upper() + ' ' + name)

    def baseline_user(self):
        identifier = uuid.uuid4().hex
        login = 'qa_' + identifier[:14]
        tel = '199' + str(int(identifier[:8], 16) % 100000000).zfill(8)
        fields = ['id', 'name', 'py', 'tel', 'frame', 'role', 'user', 'pwd', 'img', 'token', 'expire', 'data', 'more']
        values = [identifier, 'QA Before', 'qa', tel, self.state['frame_id'], self.state['role_id'], login,
                  'QA_DISABLED_LOGIN', '', '', 0, 'before', '{}']
        sql(self.state, 'INSERT INTO `user`(' + ','.join('`' + key + '`' for key in fields) + ') VALUES(' + ','.join(literal(value) for value in values) + ');')
        return {'id': identifier, 'name': 'QA After', 'frame': self.state['frame_id'], 'role': self.state['role_id'],
                'user': login, 'tel': tel, 'py': 'qa', 'img': '', 'more': '{}', 'data': 'after'}

    def run_baseline(self):
        def edit():
            fixture = self.baseline_user()
            self.success('PUT', '/user/mod-user', fixture)
            actual = sql(self.state, 'SELECT data FROM `user` WHERE id=' + literal(fixture['id']) + ';')
            assert actual == 'after', 'HTTP success did not persist the edited remark'
            return ['Actual PUT accepted original account and phone', 'MySQL stored the edited remark']
        self.case('user.edit_excludes_self_from_duplicate_check', edit)
        self.write_report()

    def user_payload(self, **overrides):
        nonce = uuid.uuid4().hex
        payload = {'name': 'QA User ' + nonce[:8], 'user': 'qa_' + nonce[:16],
                   'tel': '199' + str(int(nonce[:8], 16) % 100000000).zfill(8),
                   'frame': self.state['frame_id'], 'role': self.state['role_id'],
                   'pwd': secrets.token_urlsafe(9), 'data': 'initial remark'}
        payload.update(overrides)
        return payload

    def user_row(self, identifier):
        fields = ['id', 'name', 'py', 'tel', 'frame', 'role', 'user', 'img', 'data', 'more', 'expire']
        expression = ','.join(literal(key) + ',`' + key + '`' for key in fields)
        raw = sql(self.state, "SELECT JSON_OBJECT(" + expression + ",'pwd_digest',SHA2(pwd,256)) FROM `user` WHERE id=" + literal(identifier) + ';')
        return json.loads(raw) if raw else None

    def new_user(self, **overrides):
        payload = self.user_payload(**overrides)
        identifier = self.success('POST', '/user/add-user', payload)
        assert isinstance(identifier, str) and identifier, 'Create did not return a user ID'
        row = self.user_row(identifier)
        assert row and row['user'] == payload['user'], 'Create did not persist the requested account'
        return identifier, payload, row

    def reject_unchanged(self, path, payload, identifier):
        before = self.user_row(identifier)
        result = self.request('PUT', path, payload)
        assert result.get('code') != 10000, 'Invalid mutation was accepted'
        assert self.user_row(identifier) == before, 'Rejected mutation changed persisted data'

    def run_users(self):
        def create():
            identifier, payload, row = self.new_user()
            assert row['name'] == payload['name'] and row['frame'] == payload['frame'] and row['role'] == payload['role']
            detail = self.success('GET', '/user/query-one?id=' + urllib.parse.quote(identifier))
            assert detail['user'] == payload['user'] and not any(key in detail for key in ['pwd', 'token']), 'Details expose credentials or wrong user'
            import bcrypt
            hashed = sql(self.state, 'SELECT pwd FROM `user` WHERE id=' + literal(identifier) + ';')
            assert hashed != payload['pwd'] and bcrypt.checkpw(payload['pwd'].encode(), hashed.encode()), 'Created password hash is unusable'
            return ['Actual create without optional fields', 'MySQL profile and foreign IDs match', 'Independent BCrypt verification', 'Details do not expose password/token']
        self.case('user.create_optional_fields_and_password_hash', create)

        def unchanged():
            identifier, payload, before = self.new_user()
            update = {key: value for key, value in payload.items() if key != 'pwd'}
            update['id'] = identifier
            for _ in range(2):
                self.success('PUT', '/user/mod-user', update)
            assert self.user_row(identifier) == before, 'Unchanged saves modified stored values'
            return ['Two unchanged PUT requests succeed', 'Persisted profile and password hash stay identical']
        self.case('user.unchanged_save_is_idempotent', unchanged)

        def edit():
            identifier, payload, before = self.new_user()
            update = {key: value for key, value in payload.items() if key != 'pwd'}
            update.update({'id': identifier, 'name': 'QA Edited', 'data': 'edited remark'})
            self.success('PUT', '/user/mod-user', update)
            after = self.user_row(identifier)
            assert after['name'] == 'QA Edited' and after['data'] == 'edited remark'
            assert after['pwd_digest'] == before['pwd_digest'] and after['user'] == before['user'] and after['tel'] == before['tel']
            return ['Original account/phone pass update checks', 'Name and remark persisted', 'Password unchanged']
        self.case('user.edit_excludes_self_from_duplicate_check', edit)

        def partial():
            identifier, _, before = self.new_user()
            self.success('PUT', '/user/mod-user', {'id': identifier, 'data': 'partial update'})
            after = self.user_row(identifier)
            assert after == {**before, 'data': 'partial update'}, 'Omitted fields were changed'
            return ['Partial request changes only the supplied field in MySQL']
        self.case('user.omitted_fields_are_preserved', partial)

        def preserve_null():
            identifier, _, _ = self.new_user()
            sql(self.state, 'UPDATE `user` SET data=NULL,img=NULL,more=NULL WHERE id=' + literal(identifier) + ';')
            before = self.user_row(identifier)
            self.success('PUT', '/user/mod-user', {'id': identifier, 'name': 'QA Preserve Null'})
            assert self.user_row(identifier) == {**before, 'name': 'QA Preserve Null'}, 'Legacy NULL metadata was overwritten'
            return ['Unspecified legacy nullable fields remain SQL NULL']
        self.case('user.legacy_null_fields_are_preserved', preserve_null)

        def clear():
            identifier, _, before = self.new_user()
            for _ in range(2):
                self.success('PUT', '/user/mod-user', {'id': identifier, 'data': ''})
            assert self.user_row(identifier) == {**before, 'data': ''}, 'Cleared remark was not persisted exactly'
            return ['Explicit clear stored as empty string', 'Repeated clear succeeds', 'All other values retained']
        self.case('user.clear_remark_and_repeat', clear)

        def blank_password():
            identifier, payload, before = self.new_user()
            self.success('PUT', '/user/mod-user', {'id': identifier, 'pwd': '', 'data': 'password retained'})
            assert self.user_row(identifier)['pwd_digest'] == before['pwd_digest'], 'Blank password erased or rehashed the existing password'
            import bcrypt
            hashed = sql(self.state, 'SELECT pwd FROM `user` WHERE id=' + literal(identifier) + ';')
            assert bcrypt.checkpw(payload['pwd'].encode(), hashed.encode())
            return ['Blank password does not alter the hash', 'Original password independently verifies']
        self.case('user.blank_password_keeps_existing_credentials', blank_password)

        def change_password():
            identifier, payload, before = self.new_user()
            replacement = secrets.token_urlsafe(9)
            self.success('PUT', '/user/mod-user', {'id': identifier, 'pwd': replacement})
            import bcrypt
            hashed = sql(self.state, 'SELECT pwd FROM `user` WHERE id=' + literal(identifier) + ';')
            assert self.user_row(identifier)['pwd_digest'] != before['pwd_digest']
            assert bcrypt.checkpw(replacement.encode(), hashed.encode()) and not bcrypt.checkpw(payload['pwd'].encode(), hashed.encode())
            return ['New BCrypt hash persisted', 'New password verifies; previous password fails']
        self.case('user.password_change_updates_hash', change_password)

        def duplicate_account():
            identifier, original, before = self.new_user()
            payload = self.user_payload(user=original['user'])
            assert self.request('POST', '/user/add-user', payload).get('code') != 10000
            assert sql(self.state, 'SELECT COUNT(*) FROM `user` WHERE `user`=' + literal(original['user']) + ';') == '1'
            assert self.user_row(identifier) == before
            return ['Existing account rejected without inserting or modifying a user']
        self.case('user.duplicate_account_rejected', duplicate_account)

        def duplicate_phone():
            identifier, original, before = self.new_user()
            payload = self.user_payload(tel=original['tel'])
            assert self.request('POST', '/user/add-user', payload).get('code') != 10000
            assert sql(self.state, 'SELECT COUNT(*) FROM `user` WHERE `user`=' + literal(payload['user']) + ';') == '0'
            assert self.user_row(identifier) == before
            return ['Duplicate phone rejected; original user unchanged and no new account inserted']
        self.case('user.duplicate_phone_rejected', duplicate_phone)

        def changed_phone():
            first, _, before = self.new_user()
            _, other, _ = self.new_user()
            self.reject_unchanged('/user/mod-user', {'id': first, 'tel': other['tel']}, first)
            return ['Changing to another account phone is rejected atomically']
        self.case('user.update_phone_duplicate_rejected', changed_phone)

        def rename():
            identifier, _, _ = self.new_user()
            self.reject_unchanged('/user/mod-user', {'id': identifier, 'user': 'qa_renamed_' + uuid.uuid4().hex[:10]}, identifier)
            return ['Login identity cannot be renamed; persisted history key unchanged']
        self.case('user.login_identity_is_immutable', rename)

        for field, value in [('tel', '123'), ('frame', uuid.uuid4().hex), ('role', uuid.uuid4().hex), ('name', '')]:
            def invalid(field=field, value=value):
                identifier, _, _ = self.new_user()
                self.reject_unchanged('/user/mod-user', {'id': identifier, field: value}, identifier)
                return ['Invalid ' + field + ' rejected; complete MySQL profile unchanged']
            self.case('user.invalid_' + field + '_update_rolls_back', invalid)

        def no_password():
            payload = self.user_payload()
            del payload['pwd']
            assert self.request('POST', '/user/add-user', payload).get('code') != 10000
            assert sql(self.state, 'SELECT COUNT(*) FROM `user` WHERE `user`=' + literal(payload['user']) + ';') == '0'
            return ['No-password create rejected and no unusable account inserted']
        self.case('user.password_required_on_create', no_password)

        def unicode_name():
            name = '\u6d4b' * 32
            identifier, _, _ = self.new_user(name=name)
            assert self.user_row(identifier)['name'] == name
            self.reject_unchanged('/user/mod-user', {'id': identifier, 'name': name + '\u6d4b'}, identifier)
            return ['32 Chinese characters persist correctly', '33 characters rejected without mutation']
        self.case('user.unicode_name_boundary', unicode_name)

        def no_matches():
            query = urllib.parse.urlencode({'pageIndex': 1, 'pageSize': 10, 'name': 'qa_absent_' + uuid.uuid4().hex[:20]})
            result = self.success('GET', '/user/query-all?' + query)
            assert result.get('total') == 0 and not result.get('rows'), 'Empty query did not return an empty successful page'
            return ['No-match search returns successful empty page, not a business error']
        self.case('user.empty_search_is_not_an_error', no_matches)

        def delete_unused():
            identifier, _, _ = self.new_user()
            self.success('DELETE', '/user/del-user?id=' + urllib.parse.quote(identifier))
            assert self.user_row(identifier) is None
            return ['Actual query-parameter DELETE removes only the unreferenced test user']
        self.case('user.delete_unused_user', delete_unused)

        def delete_referenced():
            identifier, _, before = self.new_user()
            reference = uuid.uuid4().hex
            sql(self.state, 'INSERT INTO often(id,`user`,name,`key`) VALUES(' + literal(reference) + ',' + literal(identifier) + ",'QA Favorite','qa');")
            assert self.request('DELETE', '/user/del-user?id=' + urllib.parse.quote(identifier)).get('code') != 10000
            assert self.user_row(identifier) == before
            assert sql(self.state, 'SELECT COUNT(*) FROM often WHERE id=' + literal(reference) + ';') == '1'
            return ['Referenced delete rejected by actual database rules', 'User and reference both retained']
        self.case('user.delete_reference_protected', delete_referenced)

        def concurrent_duplicate():
            login = 'qa_race_' + uuid.uuid4().hex[:12]
            barrier = threading.Barrier(4)
            def create_one(_):
                payload = self.user_payload(user=login)
                barrier.wait(timeout=10)
                return self.request('POST', '/user/add-user', payload).get('code')
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(create_one, range(4)))
            actual = int(sql(self.state, 'SELECT COUNT(*) FROM `user` WHERE `user`=' + literal(login) + ';'))
            assert actual == 1 and results.count(10000) == 1, 'Concurrent duplicate create produced ' + str(actual) + ' persisted accounts'
            return ['Four concurrent HTTP creates result in exactly one account and one success']
        self.case('user.concurrent_duplicate_account_create', concurrent_duplicate)
        def concurrent_phone():
            phone = self.user_payload()['tel']
            barrier = threading.Barrier(4)
            def create_one(_):
                payload = self.user_payload(tel=phone)
                barrier.wait(timeout=10)
                return self.request('POST', '/user/add-user', payload).get('code')
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(create_one, range(4)))
            actual = int(sql(self.state, 'SELECT COUNT(*) FROM `user` WHERE tel=' + literal(phone) + ';'))
            assert actual == 1 and results.count(10000) == 1, 'Concurrent duplicate phone produced ' + str(actual) + ' accounts'
            return ['Four concurrent creates with a shared phone persist exactly one user']
        self.case('user.concurrent_duplicate_phone_create', concurrent_phone)

        def concurrent_phone_update():
            users = [self.new_user()[0] for _ in range(2)]
            phone = self.user_payload()['tel']
            barrier = threading.Barrier(2)
            def update_one(identifier):
                barrier.wait(timeout=10)
                return self.request('PUT', '/user/mod-user', {'id': identifier, 'tel': phone}).get('code')
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(update_one, users))
            actual = int(sql(self.state, 'SELECT COUNT(*) FROM `user` WHERE tel=' + literal(phone) + ';'))
            assert actual == 1 and results.count(10000) == 1, 'Concurrent phone edits violated uniqueness'
            return ['Concurrent phone edits allow exactly one writer; other user retains their phone']
        self.case('user.concurrent_duplicate_phone_update', concurrent_phone_update)

        def invalid_search():
            result = self.request('GET', '/user/query-all?' + urllib.parse.urlencode({'name': 'x' * 33}))
            assert result.get('code') != 10000 and result.get('message'), 'Invalid search must return a readable JSON error'
            return ['Overlength query returns valid UTF-8 JSON error']
        self.case('user.invalid_search_returns_readable_error', invalid_search)
        self.write_report()

    def write_report(self):
        directory = QA / 'reports'
        directory.mkdir(exist_ok=True)
        report = {'database_isolated': True, 'production_business_writes': 0, 'cases': self.results,
                  'verified': sum(row['status'] == 'verified' for row in self.results),
                  'failed': sum(row['status'] == 'failed' for row in self.results),
                  'all_system_features_accepted': False}
        (directory / 'latest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        name = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json'
        (directory / name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        if report['failed']:
            raise SystemExit(1)

    def run_auth(self):
        client = json.loads((QA / 'runtime/oauth-client.json').read_text(encoding='utf-8'))

        def grant(parameters):
            port = self.state['oauth_port']
            assert 18000 <= port <= 19999
            parameters = {**parameters, 'client_id': client['mgr-id'], 'client_secret': client['mgr-password']}
            request = urllib.request.Request('http://127.0.0.1:' + str(port) + '/oauth/token',
                                             data=urllib.parse.urlencode(parameters).encode())
            try:
                with self.opener.open(request, timeout=20) as response:
                    result = json.load(response)
                    result['access_token'] = result.get('access_token') or result.get('token')
                    return response.status, result
            except urllib.error.HTTPError as error:
                return error.code, json.load(error)

        def login(username, password):
            return grant({'grant_type': 'password', 'username': username, 'password': password})

        def lifecycle():
            identifier, payload, _ = self.new_user()
            status, result = login(payload['user'], payload['pwd'])
            known = next((message for message in ['A granted authority textual representation is required', 'Bad credentials', 'Cannot pass null or empty values', 'User account is locked', '用户不存在'] if message in str(result.get('errorMsg', ''))), 'unclassified')
            assert status == 200 and (result.get('access_token') or result.get('accessToken')), 'New account cannot actually log in: HTTP ' + str(status) + '; category=' + known + '; response fields=' + ','.join(result.keys())
            status, result = login(payload['user'], 'intentionally-wrong')
            assert not result.get('access_token') and (result.get('error') or result.get('errorMsg')), 'Incorrect password authenticated'
            self.success('PUT', '/user/mod-user', {'id': identifier, 'pwd': '', 'data': 'retain login'})
            status, result = login(payload['user'], payload['pwd'])
            assert status == 200 and result.get('access_token'), 'Unchanged-password save broke login'
            replacement = secrets.token_urlsafe(9)
            self.success('PUT', '/user/mod-user', {'id': identifier, 'pwd': replacement})
            status, result = login(payload['user'], payload['pwd'])
            assert not result.get('access_token') and (result.get('error') or result.get('errorMsg')), 'Old password still authenticated'
            status, result = login(payload['user'], replacement)
            assert status == 200 and result.get('access_token'), 'Changed password cannot actually log in'
            (QA / 'runtime/browser-session.json').write_text(json.dumps({'token': result['access_token']}), encoding='utf-8')
            return ['Actual isolated OAuth grants a token to the new account', 'Wrong password rejected',
                    'Blank-password save preserves login', 'Password change rejects old password and accepts new password']
        self.case('auth.actual_user_password_lifecycle', lifecycle)
        def custom_role():
            name = 'QA Login Role ' + uuid.uuid4().hex[:8]
            identifier = self.success('POST', '/role/add-role', {'name': name, 'data': '', 'root': '[]', 'auth': '{}'})
            assert isinstance(identifier, str) and identifier
            keyword = sql(self.state, 'SELECT keyword FROM role WHERE id=' + literal(identifier) + ';')
            import base64
            expected = 'R_' + base64.urlsafe_b64encode(bytes.fromhex(identifier.replace('-', ''))).decode().rstrip('=')
            assert keyword == expected and len(keyword) == 24, 'New role has an empty or unstable permission identity'
            _, payload, _ = self.new_user(role=identifier)
            status, result = login(payload['user'], payload['pwd'])
            assert status == 200 and result.get('access_token'), 'User assigned a newly created role cannot log in'
            return ['Role created through actual C1 API', 'Stable role authority persisted in MySQL',
                    'New user assigned that role receives an actual OAuth token']
        self.case('auth.new_custom_role_can_log_in', custom_role)
        def refresh():
            _, payload, _ = self.new_user()
            status, result = login(payload['user'], payload['pwd'])
            assert status == 200 and result.get('access_token') and result.get('refreshToken'), 'Initial login did not return both credentials'
            status, renewed = grant({'grant_type': 'refresh_token', 'refresh_token': result['refreshToken']})
            assert status == 200 and renewed.get('access_token'), 'Real refresh grant failed'
            import base64
            def claims(token):
                value = token.split('.')[1]
                return json.loads(base64.urlsafe_b64decode(value + '=' * (-len(value) % 4)))
            assert claims(renewed['access_token'])['user_name'] == payload['user'], 'Refresh changed the authenticated identity'
            _, invalid = grant({'grant_type': 'refresh_token', 'refresh_token': 'qa_invalid_' + uuid.uuid4().hex})
            assert not invalid.get('access_token') and (invalid.get('errorMsg') or invalid.get('error')), 'Invalid refresh token accepted'
            return ['Actual OAuth refresh grants a token for the same user', 'Malformed refresh credential rejected without issuing a token']
        self.case('auth.actual_refresh_and_invalid_refresh', refresh)
        self.write_report()

    def run_avatars(self):
        import struct
        import zlib
        def chunk(name, data):
            return struct.pack('!I', len(data)) + name + data + struct.pack('!I', zlib.crc32(name + data) & 0xffffffff)
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 16, 16, 8, 6, 0, 0, 0))
        png += chunk(b'IDAT', zlib.compress((b'\x00' + bytes([0, 160, 200, 255]) * 16) * 16)) + chunk(b'IEND', b'')
        fixture = QA / 'runtime/fixtures/avatar.png'
        fixture.parent.mkdir(exist_ok=True)
        fixture.write_bytes(png)

        def upload(content, filename='avatar.png'):
            boundary = 'qa' + uuid.uuid4().hex
            body = ('--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' + filename +
                    '"\r\nContent-Type: image/png\r\n\r\n').encode() + content + ('\r\n--' + boundary + '--\r\n').encode()
            port = self.state['supportinfo_port']
            assert 18000 <= port <= 19999
            request = urllib.request.Request('http://127.0.0.1:' + str(port) + '/attachment/avatar', data=body,
                    headers={'Content-Type': 'multipart/form-data; boundary=' + boundary, 'Authorization': 'Bearer ' + self.token})
            try:
                with self.opener.open(request, timeout=20) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                return {'code': error.code}

        def count():
            return sql(self.state, 'SELECT COUNT(*) FROM annex;')

        def actual_avatar():
            result = upload(png)
            assert result.get('code') == 10000 and result.get('data', {}).get('id'), 'Valid image upload failed'
            identifier = result['data']['id']
            row = json.loads(sql(self.state, "SELECT JSON_OBJECT('type',file_type,'storage',save_type,'path',save_path) FROM annex WHERE id=" + literal(identifier) + ';'))
            assert row['storage'] == 'Local' and row['type'] == 'png'
            path = QA / 'runtime/attachments' / row['path']
            assert path.resolve().is_file() and path.read_bytes() == png, 'Actual stored bytes differ'
            url = 'http://127.0.0.1:' + str(self.state['supportinfo_port']) + '/attachment/avatar/' + identifier
            request = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + self.token})
            with self.opener.open(request, timeout=20) as response:
                assert response.headers.get_content_type() == 'image/png' and response.read() == png, 'Download differs from original upload'
            user, _, _ = self.new_user()
            self.success('PUT', '/user/mod-user', {'id': user, 'img': identifier})
            assert sql(self.state, 'SELECT img FROM `user` WHERE id=' + literal(user) + ';') == identifier
            detail = self.success('GET', '/user/query-one?id=' + user)
            assert detail['img'] == identifier, 'Reopened user lost avatar attachment identity'
            return ['Real multipart upload writes PNG bytes and an attachment row', 'Actual HTTP download returns identical bytes and image MIME',
                    'User update stores the attachment ID; reopened detail returns the same ID']
        self.case('avatar.actual_upload_download_and_user_association', actual_avatar)

        for name, content in [('empty', b''), ('disguised_html', b'<html>not an image</html>'), ('oversized', b'x' * (5 * 1024 * 1024 + 1))]:
            def reject(content=content):
                before = count()
                files_before = sorted(str(p) for p in (QA / 'runtime/attachments').rglob('*') if p.is_file())
                result = upload(content)
                assert result.get('code') != 10000, 'Invalid file accepted'
                assert count() == before, 'Rejected file created metadata'
                assert sorted(str(p) for p in (QA / 'runtime/attachments').rglob('*') if p.is_file()) == files_before, 'Rejected file left stored bytes'
                return ['Rejected actual multipart payload; no attachment record or stored file added']
            self.case('avatar.reject_' + name + '_without_writes', reject)

        def traversal():
            result = upload(png, '../../qa-escape.png')
            assert result.get('code') == 10000
            identifier = result['data']['id']
            row = json.loads(sql(self.state, "SELECT JSON_OBJECT('name',name,'path',save_path) FROM annex WHERE id=" + literal(identifier) + ';'))
            assert row['name'] == 'qa-escape.png' and row['path'] == 'avatars/' + identifier + '.png'
            assert (QA / 'runtime/attachments' / row['path']).read_bytes() == png
            return ['Client filename path is removed; actual file is stored under generated attachment identity']
        self.case('avatar.filename_cannot_choose_storage_path', traversal)
        self.write_report()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['bootstrap', 'baseline', 'users', 'auth', 'avatars'])
    args = parser.parse_args()
    if args.action == 'bootstrap':
        bootstrap()
    elif args.action == 'baseline':
        Suite(read_state()).run_baseline()
    elif args.action == 'auth':
        Suite(read_state()).run_auth()
    elif args.action == 'avatars':
        Suite(read_state()).run_avatars()
    else:
        Suite(read_state()).run_users()
