#!/usr/bin/env python3
"""Offline source reconstruction: pins, hashes, subset and overwrite safety."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from fetch_dependencies import fetch


class FetchTests(unittest.TestCase):
    def test_reconstruct_subset_and_refuse_corruption_or_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);repo=root/'upstream';repo.mkdir()
            def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL)
            git('init');(repo/'LICENSE').write_text('fixture license\n')
            for name in ['needed','unused']:
                (repo/name).mkdir();(repo/name/'sample').write_text('before\n')
            git('add','.');git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','base')
            patch=b'--- a/needed/sample\n+++ b/needed/sample\n@@ -1 +1 @@\n-before\n+after\n'
            (root/'fix.patch').write_bytes(patch)
            digest=lambda b:hashlib.sha256(b).hexdigest()
            source={'id':'fixture','url':str(repo),'target_revision':git('rev-parse','HEAD').decode().strip(),
                    'patches':['fix.patch'],'patch_sha256':{'fix.patch':digest(patch)},
                    'license_sha256':digest((repo/'LICENSE').read_bytes()),
                    'package_roots':{'needed':'selected'},'patched_files_sha256':{'needed/sample':digest(b'after\n')}}
            target=root/'vendor'
            (root/'fix.patch').write_bytes(patch+b'corrupt')
            with self.assertRaisesRegex(ValueError,'Patch hash mismatch'):fetch(root,source,target)
            self.assertFalse(target.exists())
            (root/'fix.patch').write_bytes(patch)
            fetch(root,source,target)
            self.assertEqual((target/'selected/sample').read_text(),'after\n')
            self.assertFalse((target/'unused').exists());self.assertFalse((target/'.git').exists())
            self.assertEqual((target/'LICENSE').read_text(),'fixture license\n')
            with self.assertRaisesRegex(FileExistsError,'refusing to overwrite'):fetch(root,source,target)
            source['patched_files_sha256']['needed/sample']=digest(b'wrong')
            with self.assertRaisesRegex(ValueError,'Patched source hash mismatch'):fetch(root,source,root/'bad')
            self.assertFalse((root/'bad').exists())


if __name__=='__main__':unittest.main()
