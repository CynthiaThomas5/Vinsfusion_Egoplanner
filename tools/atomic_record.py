"""Publish a complete JSON evidence record with a same-filesystem atomic rename."""
import json
import os
from pathlib import Path
import stat
import uuid


def write_json_atomic(path, data, **json_options):
    path=Path(path)
    temporary=path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    mode=stat.S_IMODE(path.stat().st_mode) if path.exists() else None
    try:
        # Exclusive text creation preserves the caller's normal umask, unlike a
        # root-only mkstemp file that the host-side evaluator could not read.
        with temporary.open('x',encoding='utf-8') as stream:
            json.dump(data,stream,**json_options)
            stream.write('\n');stream.flush();os.fsync(stream.fileno())
        if mode is not None:temporary.chmod(mode)
        os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)
