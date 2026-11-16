"""Bounded scheduling gate for the dedicated local QA JVM, restored in finally."""
import contextlib,json,os,subprocess
from pathlib import Path
from acceptance import QA

def run(command):
    result=subprocess.run([str(x) for x in command],capture_output=True,text=True)
    if result.returncode:raise RuntimeError('QA read gate helper failed: '+result.stderr[-1800:])
    return result.stdout

def identity(state):
    pid=int(state['purchase_pid'])
    command=run(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process -Filter 'ProcessId="+str(pid)+"' | Select-Object Name,CommandLine | ConvertTo-Json -Compress"])
    process=json.loads(command);line=process.get('CommandLine','').replace('\\','/').lower()
    expected=str(QA.resolve()/'runtime/java/purchase-').replace('\\','/').lower()
    if process.get('Name','').lower()!='java.exe' or expected not in line or '--server.port=18023' not in line or '--spring.application.name=qa-purchase' not in line:raise RuntimeError('Refusing to attach outside the dedicated QA purchase JVM')
    return pid

@contextlib.contextmanager
def list_read_gate(state,kind='order'):
    if kind not in ('order','purchase'):raise ValueError('Unknown QA list gate')
    pid=identity(state)
    jdk=Path(os.environ.get('JAVA_HOME','C:/Program Files/Java/jdk1.8.0_311'))
    if not (jdk/'lib/tools.jar').is_file():jdk=Path('C:/Program Files/Java/jdk1.8.0_311')
    if not (jdk/'lib/tools.jar').is_file():raise RuntimeError('JDK8 tools.jar is required for the local QA gate')
    root=QA/'runtime/read-gate';classes=root/'classes';classes.mkdir(parents=True,exist_ok=True)
    run([jdk/'bin/javac.exe','-XDignore.symbol.file','-cp',jdk/'lib/tools.jar','-d',classes,QA/'read_gate/QaReadGate.java',QA/'read_gate/AttachReadGate.java'])
    manifest=root/'manifest.mf';manifest.write_text('Manifest-Version: 1.0\nAgent-Class: QaReadGate\nCan-Retransform-Classes: true\n\n',encoding='ascii')
    jar=root/'qa-read-gate.jar';run([jdk/'bin/jar.exe','cfm',jar,manifest,'-C',classes,'.'])
    for name in ['armed','entered','resume','timed-out']:
        path=root/name
        if path.exists():path.unlink()
    def attach(mode):
        identity(state)
        run([jdk/'bin/java.exe','-cp',str(classes)+os.pathsep+str(jdk/'lib/tools.jar'),'AttachReadGate',str(pid),jar,mode])
    attach(('on:' if kind=='order' else 'on-purchase:')+str(root.resolve()))
    try:yield root
    finally:
        (root/'resume').write_text('resume',encoding='ascii')
        attach('off')
