"""Read-only Linux process identity checks for active navigation tasks."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    start_time_ticks: int


def _read_identity(proc_entry):
    try:
        cmdline = (proc_entry / 'cmdline').read_bytes().split(b'\0')
        argv0 = cmdline[0].decode(errors='replace') if cmdline else ''
        if not argv0:
            return None
        stat = (proc_entry / 'stat').read_text(encoding='utf-8')
        # The command field is parenthesized and may contain spaces.
        fields_after_comm = stat[stat.rfind(')') + 2:].split()
        start_time_ticks = int(fields_after_comm[19])
        return argv0, start_time_ticks
    except (OSError, ValueError, IndexError):
        return None


def find_process_identities(executable, proc_root='/proc'):
    """Find exact argv[0] basename matches without invoking a shell."""
    expected = str(executable).strip()
    if not expected or Path(expected).name != expected:
        raise ValueError('executable must be a basename')
    identities = []
    try:
        entries = Path(proc_root).iterdir()
        for entry in entries:
            if not entry.name.isdigit():
                continue
            observed = _read_identity(entry)
            if observed is None:
                continue
            argv0, start_time_ticks = observed
            if Path(argv0).name == expected:
                identities.append(ProcessIdentity(int(entry.name), start_time_ticks))
    except OSError:
        return ()
    return tuple(sorted(identities, key=lambda identity: identity.pid))


def process_identity_is_running(identity, proc_root='/proc'):
    """Match both PID and kernel start time to reject PID reuse."""
    if not isinstance(identity, ProcessIdentity):
        return False
    observed = _read_identity(Path(proc_root) / str(identity.pid))
    return observed is not None and observed[1] == identity.start_time_ticks
