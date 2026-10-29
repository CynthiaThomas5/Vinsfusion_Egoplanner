import json
from pathlib import Path
import tempfile
import threading
import unittest
from atomic_record import write_json_atomic

class AtomicRecordTests(unittest.TestCase):
    def test_reader_sees_old_record_until_new_record_is_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'flight.json';p.write_text('{"old":true}\n');p.chmod(0o640)
            entered=threading.Event();release=threading.Event();errors=[]
            class DelayedEncoder(json.JSONEncoder):
                def iterencode(self,value,*args,**kwargs):
                    yield '{"new":';entered.set()
                    if not release.wait(5):raise RuntimeError('test release timeout')
                    yield 'true}'
            def writer():
                try:write_json_atomic(p,{},cls=DelayedEncoder)
                except BaseException as exc:errors.append(exc)
            t=threading.Thread(target=writer);t.start()
            try:
                self.assertTrue(entered.wait(5));self.assertEqual(json.loads(p.read_text()),{'old':True})
            finally:release.set();t.join(5)
            self.assertFalse(t.is_alive());self.assertEqual(errors,[]);self.assertEqual(json.loads(p.read_text()),{'new':True});self.assertEqual(p.stat().st_mode&0o777,0o640)
            self.assertEqual(list(Path(tmp).glob('*.tmp')),[])
    def test_serialization_failure_preserves_old_record_and_cleans_temporary(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'flight.json';p.write_text('{"old":true}\n')
            with self.assertRaises(TypeError):write_json_atomic(p,{'new':object()})
            self.assertEqual(p.read_text(),'{"old":true}\n');self.assertEqual([x.name for x in Path(tmp).iterdir()],['flight.json'])
