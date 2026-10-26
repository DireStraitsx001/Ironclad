#!/usr/bin/env python3
"""IRONCLAD Switchboard preview, independently inspired by OnionOS GameSwitcher.
Read-only. Never launches/kills games or auto-loads save states.
"""
import json,os,re,sys,subprocess
from pathlib import Path
MAX=2*1024*1024
STATE=re.compile(r'\\.state(?:\\.auto|\\d+)?$',re.I)
def parse(home=Path('/home/ark'),tf2=Path('/roms2')):
    out=[];seen=set()
    sources=[home/'.config/retroarch/content_history.lpl',home/'.config/retroarch32/content_history.lpl',
             home/'.config/retroarch/playlists/content_history.lpl']
    for src in sources:
        if not src.is_file() or src.is_symlink() or src.stat().st_size>MAX:continue
        try: obj=json.loads(src.read_text(encoding='utf-8'))
        except (OSError,ValueError,UnicodeError): continue
        items=obj.get('items',[]) if isinstance(obj,dict) else []
        if not isinstance(items,list): continue
        for item in items:
            if not isinstance(item,dict):continue
            raw=item.get('path')
            if not isinstance(raw,str) or not raw.startswith('/') or '\\x00' in raw or '\\n' in raw:continue
            if raw.startswith('/roms/'):raw=str(tf2)+raw[5:]
            path=Path(raw)
            try: rel=path.relative_to(tf2)
            except ValueError:continue
            if len(rel.parts)<2 or '..' in rel.parts or not path.is_file():continue
            if any(p.is_symlink() for p in (path,*path.parents) if p!=tf2.parent and (p==tf2 or tf2 in p.parents)):continue
            if str(path) in seen:continue
            seen.add(str(path))
            label=item.get('label') or path.stem
            if not isinstance(label,str):label=path.stem
            label=''.join(c for c in label if c.isprintable()).strip()[:65]
            state=any(f.is_file() and not f.is_symlink() and STATE.search(f.name)
                      for f in path.parent.glob(path.name+'.state*'))
            out.append({'label':label,'path':str(path),'state_file_present':state})
            if len(out)>=30:return out
    return out
def main():
    tf2=Path('/roms2')
    if not tf2.is_dir() or tf2.is_symlink():raise RuntimeError('TF2 unavailable')
    mountinfo=Path('/proc/self/mountinfo').read_text()
    if not any(len(x)>5 and x[4]=='/roms2' for x in (s.split() for s in mountinfo.splitlines())):
        raise RuntimeError('TF2 is not mounted')
    if tf2.stat().st_dev==Path('/').stat().st_dev or tf2.stat().st_dev==Path('/roms').stat().st_dev:
        raise RuntimeError('TF2 must be separate from TF1')
    entries=parse(tf2=tf2)
    if '--json' in sys.argv:
        print(json.dumps(entries,indent=2));return
    if not entries:
        print('No RetroArch recent games found on TF2.');return
    dialog=Path('/usr/bin/dialog')
    if not dialog.is_file():
        for i,x in enumerate(entries,1):print(i,x['label']);return
    args=[str(dialog),'--clear','--title','IRONCLAD Switchboard Preview','--menu',
          'Browse only; game launch and resume are disabled','19','70','12']
    for i,x in enumerate(entries,1):
        args += [str(i),(x['label'][:50]+(' [state]' if x['state_file_present'] else ''))[:56]]
    result=subprocess.run(args,stderr=subprocess.PIPE,text=True,check=False)
    if result.returncode or not result.stderr.strip().isdigit():return
    index=int(result.stderr.strip())-1
    if 0<=index<len(entries):
        e=entries[index]
        msg=e['label']+'\\n\\n'+e['path']+'\\n\\nState filename detected: '+str(e['state_file_present'])+'\\nCompatibility NOT verified. No game launched.'
        subprocess.run([str(dialog),'--msgbox',msg,'17','70'],check=False)
if __name__=='__main__':
    try: main()
    except (RuntimeError,OSError) as ex:print('Switchboard unavailable:',ex,file=sys.stderr);sys.exit(1)
