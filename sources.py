"""Public Enchor API; only public chart files are downloaded."""
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from convert import clean
from packages import MAX_BYTES


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKD", clean(text)).casefold() if c.isalnum())


def request_json(url, body):
    request = Request(url, json.dumps(body).encode(), {
        "Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": "ParadiddleCLI/1.0"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
                if len(raw) > 16 * 1024 * 1024:
                    raise ValueError("Search response exceeds size limit")
                return json.loads(raw)
        except HTTPError as exc:
            if exc.code not in {429, 502, 503, 504} or attempt == 2:
                raise
            time.sleep(1 + attempt)


def filter_charts(rows, song, artist):
    result, seen = [], set()
    for row in rows:
        if normalized(row.get("artist") or "") != normalized(artist):
            continue
        if song is not None and normalized(row.get("name") or "") != normalized(song):
            continue
        notes = row.get("notesData") or {}
        instruments = notes.get("instruments")
        if instruments is not None:
            has_drums = "drums" in instruments
        else:
            has_drums = any(isinstance(row.get(k), (int, float)) and row[k] >= 0
                            for k in ("diff_drums", "diff_drums_real"))
        digest = row.get("md5") or ""
        if has_drums and re.fullmatch("[a-fA-F0-9]{32}", digest) and digest not in seen:
            seen.add(digest)
            result.append(row)
    return result


def search(song, artist):
    if not normalized(artist) or (song is not None and not normalized(song)):
        raise ValueError("Enter an artist and, if specified, a valid song title")
    rows = []
    # Use one search term; Enchor's free-text search can act like OR.
    # Always filter artist locally, and title when supplied.
    for page in range(1, 21):
        data = request_json("https://api.enchor.us/search",
                            {"search": song if song is not None else artist, "page": page, "per_page": 250})
        if not isinstance(data.get("data"), list):
            raise ValueError("Enchor returned an unexpected search response")
        batch = data["data"]
        rows.extend(batch)
        if not batch or page * 250 >= int(data.get("found", 0)):
            matches = filter_charts(rows, song, artist)
            if song is None:
                matches.sort(key=lambda row: (normalized(row.get("name") or ""),
                                              normalized(row.get("charter") or ""), row["md5"]))
            return matches
    raise ValueError("Search exceeds 5,000 results; use a more specific full song title")


def download(chart, cache: Path) -> Path:
    digest = chart.get("md5") or ""
    if not re.fullmatch("[a-fA-F0-9]{32}", digest):
        raise ValueError("Invalid chart identifier")
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / f"{digest}.sng"
    if dest.is_file():
        return dest
    partial = dest.with_suffix(".part")
    url = f"https://files.enchor.us/{digest}.sng"
    started = time.monotonic()
    try:
        with urlopen(Request(url, headers={"User-Agent": "ParadiddleCLI/1.0"}), timeout=30) as response:
            expected = int(response.headers.get("Content-Length", 0))
            if expected > MAX_BYTES:
                raise ValueError("Download exceeds 1 GiB limit")
            total, reported = 0, 0
            with partial.open("wb") as out:
                while block := response.read(1024 * 1024):
                    total += len(block)
                    if total > MAX_BYTES or time.monotonic() - started > 600:
                        raise ValueError("Download exceeded size/time limit")
                    out.write(block)
                    if total - reported >= 10 * 1024 * 1024:
                        print(f"  Downloaded {total // (1024*1024)} MB", flush=True)
                        reported = total
            if expected and total != expected:
                raise ValueError("Incomplete download; try again")
        with partial.open("rb") as f:
            if f.read(6) != b"SNGPKG":
                raise ValueError("Download is not an SNG chart")
        partial.replace(dest)
    finally:
        partial.unlink(missing_ok=True)
    return dest
