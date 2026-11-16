"""Build OAuth in a separate Maven project; leave running service artifacts alone."""
from pathlib import Path
import shutil
import os
import argparse
import xml.etree.ElementTree as ET
from acceptance import ROOT, QA

parser = argparse.ArgumentParser()
parser.add_argument('--module', choices=['psi-oauth2', 'psi-j7-supportinfo', 'psi-j2-storemanagement', 'psi-j6-basic_Information', 'psi-sale', 'psi-j3-purchase', 'psi-j6-payment_order', 'psi-j1-homepage', 'psi-fund', 'psi-gateway', 'psi-login'], default='psi-oauth2')
arguments = parser.parse_args()
source = ROOT / 'zero-one-12psi/psi-java' / arguments.module
project = {'psi-oauth2': 'oauth-project', 'psi-j7-supportinfo': 'supportinfo-project',
           'psi-j2-storemanagement': 'store-project', 'psi-j6-basic_Information': 'basic-project',
           'psi-sale': 'sale-project', 'psi-j3-purchase': 'purchase-project', 'psi-j6-payment_order': 'payment-project', 'psi-j1-homepage': 'homepage-project', 'psi-fund': 'fund-project', 'psi-gateway': 'gateway-project', 'psi-login': 'login-project'}[arguments.module]
destination = QA / 'runtime/java' / project
destination.mkdir(parents=True, exist_ok=True)
# The QA mirror is generated source, never an independent place to edit code.
# Remove obsolete files individually so a deleted insecure implementation/test
# cannot silently survive in the candidate built by Maven.
source_root=(source/'src').resolve()
mirror_root=(destination/'src').resolve()
assert (QA/'runtime/java').resolve() in mirror_root.parents
expected={item.relative_to(source_root) for item in source_root.rglob('*') if item.is_file()}
if mirror_root.exists():
    for item in mirror_root.rglob('*'):
        if item.is_file() and item.relative_to(mirror_root) not in expected:
            assert mirror_root in item.resolve().parents
            item.unlink()
for item in (source / 'src').rglob('*'):
    target = destination / item.relative_to(source)
    if item.is_dir():
        target.mkdir(parents=True, exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(item), str(target))
namespace = 'http://maven.apache.org/POM/4.0.0'
ET.register_namespace('', namespace)
tree = ET.parse(source / 'pom.xml')
parent = tree.getroot().find('{' + namespace + '}parent')
relative = parent.find('{' + namespace + '}relativePath')
if relative is None:
    relative = ET.SubElement(parent, '{' + namespace + '}relativePath')
relative.text = os.path.relpath(str(source.parent / 'pom.xml'), str(destination)).replace('\\', '/')
tree.write(destination / 'pom.xml', encoding='utf-8', xml_declaration=True)
print('Isolated Maven project prepared: ' + arguments.module)
