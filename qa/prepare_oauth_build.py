"""Build OAuth in a separate Maven project; leave running service artifacts alone."""
from pathlib import Path
import shutil
import os
import argparse
import xml.etree.ElementTree as ET
from acceptance import ROOT, QA

parser = argparse.ArgumentParser()
parser.add_argument('--module', choices=['psi-oauth2', 'psi-j7-supportinfo'], default='psi-oauth2')
arguments = parser.parse_args()
source = ROOT / 'zero-one-12psi/psi-java' / arguments.module
project = 'oauth-project' if arguments.module == 'psi-oauth2' else 'supportinfo-project'
destination = QA / 'runtime/java' / project
destination.mkdir(parents=True, exist_ok=True)
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
