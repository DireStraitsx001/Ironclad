#!/usr/bin/env python3
import importlib.util,json,tempfile,unittest
from pathlib import Path
p=Path(__file__).with_name('switchboard.py')
s=importlib.util.spec_from_file_location('switchboard',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class TestHistory(unittest.TestCase):
    def test_tf2_only(self):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d); tf=t/'roms2';(tf/'gba').mkdir(parents=True)
            rom=tf/'gba/Test.gba';rom.write_bytes(b'x')
            (rom.parent/'Test.gba.state.auto').write_bytes(b'0')
            home=t/'home';h=home/'.config/retroarch';h.mkdir(parents=True)
            (h/'content_history.lpl').write_text(json.dumps({'items':[{'path':str(rom)}, {'path':str(t/'outside.gba')},{'path':str(rom)}]}))
            found=m.parse(home,tf)
            self.assertEqual(len(found),1)
            self.assertTrue(found[0]['state_file_present'])
    def test_corrupt_history(self):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d);(t/'roms2').mkdir()
            h=t/'home/.config/retroarch';h.mkdir(parents=True)
            (h/'content_history.lpl').write_text('{oops')
            self.assertEqual(m.parse(t/'home',t/'roms2'),[])
if __name__=='__main__':unittest.main()
