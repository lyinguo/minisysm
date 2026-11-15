"""Build a versioned C++ acceptance executable without replacing a running production EXE."""
import argparse
import datetime
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / 'zero-one-12psi/psi-cpp/out/build/x64-Debug'


def main(module):
    if not re.fullmatch(r'psi-c[1-6]-[a-z_]+', module):
        raise RuntimeError('Unknown C++ application target')
    cache = (BUILD / 'CMakeCache.txt').read_text(encoding='utf-8-sig')
    def cached(key):
        found = re.search(r'^' + re.escape(key) + r':\w+=(.+)$', cache, re.M)
        if not found:
            raise RuntimeError('CMake cache key missing: ' + key)
        return found.group(1).strip()
    ninja = cached('CMAKE_MAKE_PROGRAM')
    compiler = cached('CMAKE_CXX_COMPILER').replace('\\', '/')
    vcvars = os.environ.get('PSI_VCVARS_PATH') or compiler.split('/VC/Tools/')[0] + '/VC/Auxiliary/Build/vcvars64.bat'
    commands = subprocess.check_output([ninja, '-t', 'commands', module + '/' + module + '.exe'], cwd=BUILD).decode('utf-8', errors='replace')
    linkers = [line for line in commands.splitlines() if 'vs_link_exe' in line and module + '.exe' in line]
    if len(linkers) != 1:
        raise RuntimeError('Expected exactly one application link command')
    stamp = datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    directory = ROOT / 'qa/runtime/cpp' / module
    directory.mkdir(parents=True, exist_ok=True)
    output = directory / (module + '-' + stamp + '.exe')
    link = linkers[0]
    for flag, extension in [('out', '.exe'), ('pdb', '.pdb'), ('implib', '.lib')]:
        target = output.with_suffix(extension).as_posix()
        link, count = re.subn(r'(/' + flag + r':)(?:"[^"]+"|[^\s"]+)', lambda match: match.group(1) + '"' + target + '"', link, flags=re.I)
        if flag == 'out' and count != 1:
            raise RuntimeError('Refusing to link without an isolated output path')
    graph = (BUILD / 'build.ninja').read_text(encoding='utf-8-sig')
    objects = []
    for line in graph.splitlines():
        if line.startswith('build ') and '.obj:' in line:
            target = line[6:line.index(': ')]
            if target.replace('\\', '/').startswith(module + '/CMakeFiles/' + module + '.dir/'):
                objects.append(target)
    if not objects:
        raise RuntimeError('No application objects found')
    batch = directory / ('build-' + stamp + '.bat')
    body = ['@echo off', 'call "' + vcvars + '" >nul', 'if errorlevel 1 exit /b 1',
            'set VSLANG=1033', 'cd /d "' + str(BUILD) + '"',
            '"' + ninja + '" -j 2 ' + ' '.join('"' + item + '"' for item in objects),
            'if errorlevel 1 exit /b 1', link, 'exit /b %errorlevel%']
    batch.write_text('\n'.join(body) + '\n', encoding='utf-8')
    log = directory / ('build-' + stamp + '.log')
    with log.open('wb') as stream:
        result = subprocess.run(['cmd.exe', '/d', '/c', str(batch)], stdout=stream, stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode or not output.exists():
        raise RuntimeError('C++ acceptance build failed; inspect ' + str(log))
    (directory / 'latest.txt').write_text(str(output), encoding='utf-8')
    print('Isolated C++ executable built: ' + str(output))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('module')
    main(parser.parse_args().module)
