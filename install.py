"""Optional copying to the user's configured Paradiddle Songs directory."""
import os
import shutil
import tempfile
from pathlib import Path


def configured_songs_dir(root: Path) -> Path | None:
    env = root / ".env"
    if not env.exists():
        return None
    value = ""
    for line in env.read_text(encoding="utf-8-sig").splitlines():
        key, separator, candidate = line.strip().partition("=")
        if separator and key.strip() == "PARADIDDLE_SONGS_DIR":
            value = candidate.strip()
            if value.startswith(("'", '"')):
                if len(value) < 2 or value[-1] != value[0]:
                    raise ValueError("Unclosed quote in .env PARADIDDLE_SONGS_DIR")
                value = value[1:-1]
            else:
                value = value.split(" #", 1)[0].rstrip()
    if not value:
        return None
    destination = Path(os.path.expandvars(value)).expanduser()
    if not destination.is_absolute():
        raise ValueError("PARADIDDLE_SONGS_DIR must be an absolute path to your existing Songs folder")
    if not destination.is_dir():
        raise ValueError("PARADIDDLE_SONGS_DIR must point to an existing Songs folder")
    return destination.resolve()


def copy_song(source: Path, songs_dir: Path) -> Path:
    target = songs_dir / source.name
    if target.resolve() == source.resolve():
        return target
    if target.exists():
        raise FileExistsError(f"Song already exists in Paradiddle: {target}; nothing was overwritten")
    # Stage on the same filesystem; expose the final folder only when complete.
    with tempfile.TemporaryDirectory(prefix=".paradiddle-copy-", dir=songs_dir) as tmp:
        staged = Path(tmp) / source.name
        shutil.copytree(source, staged)
        if target.exists():
            raise FileExistsError(f"Song already exists in Paradiddle: {target}")
        staged.rename(target)
    return target
