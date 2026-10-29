#!/usr/bin/env python3
"""A delivery must preserve runnable source and omit local/private state."""
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
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

    def test_missing_historical_archive_exports_verified_local_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';(root/'dependencies').mkdir(parents=True);(root/'config').mkdir()
            (root/'dependencies/sources.json').write_text(json.dumps({'container_rebuild':{'portable_image_bundle':{'path':'absent','sha256':'old'}}}))
            (root/'config/runtime.json').write_text(json.dumps({'image':'fixed:tag','image_id':'sha256:verified'}))
            output=Path(tmp)/'delivery'
            with patch('export_project.subprocess.check_output',return_value='sha256:verified\n'), patch('export_project.save_local_image',side_effect=lambda image,path:Path(path).write_bytes(b'verified image archive')) as save:
                report=export(root,output)
            save.assert_called_once();self.assertTrue(report['image_included'])
            self.assertEqual(report['image_export']['image_id'],'sha256:verified')
            self.assertIn('container-images.tar.zst',report['artifacts_sha256'])

    def test_wrong_local_image_refuses_before_creating_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'root';(root/'dependencies').mkdir(parents=True);(root/'config').mkdir()
            (root/'dependencies/sources.json').write_text(json.dumps({'container_rebuild':{'portable_image_bundle':{'path':'absent','sha256':'old'}}}))
            (root/'config/runtime.json').write_text(json.dumps({'image':'fixed:tag','image_id':'sha256:verified'}))
            output=Path(tmp)/'delivery'
            with patch('export_project.subprocess.check_output',return_value='sha256:wrong\n'):
                with self.assertRaisesRegex(ValueError,'identity mismatch'):export(root,output)
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
