#!/usr/bin/env python3
"""A delivery must preserve runnable source and omit local/private state."""
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from export_project import export


class ExportTests(unittest.TestCase):
    def test_source_delivery_excludes_private_and_generated_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';root.mkdir()
            (root/'start.sh').write_text('#!/usr/bin/env bash\nexit 0\n')
            (root/'start.sh').chmod(0o755)
            for name in ['src/own/pkg/node.py','config/active.json','config/local/token.json','collaboration/dialogues/raw/chat.md','tools/__pycache__/cache.pyc','artifacts/runs/log','src/vendor/copied/secret.py']:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture\n')
            p=root/'dependencies/sources.json';p.parent.mkdir();p.write_text(json.dumps({'container_rebuild':{'portable_image_bundle':{'path':'absent','sha256':'x'}}}))
            output=Path(tmp)/'delivery';report=export(root,output,code_only=True)
            with tarfile.open(output/'project-source.tar.gz') as t:names=t.getnames()
            self.assertIn('project/src/own/pkg/node.py',names);self.assertIn('project/config/active.json',names)
            self.assertIn('project/start.sh',names)
            with tarfile.open(output/'project-source.tar.gz') as t:
                self.assertTrue(t.getmember('project/start.sh').mode & 0o111)
            self.assertFalse(any(word in n for n in names for word in ['/local/','/raw/','/__pycache__/','/runs/','/copied/']))
            self.assertFalse(report['image_included'])
            with self.assertRaises(FileExistsError):export(root,output,code_only=True)
            with self.assertRaisesRegex(ValueError,'image bundle'):export(root,Path(tmp)/'full',code_only=False)
            self.assertFalse((Path(tmp)/'full').exists())


if __name__=='__main__':unittest.main()
