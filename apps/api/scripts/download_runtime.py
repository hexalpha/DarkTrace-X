"""Download official, workspace-local service distributions for Windows verification."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[3] / ".runtime"
PACKAGES = {
    "postgres": "https://sbp.enterprisedb.com/getfile.jsp?fileid=1260494",
    "elasticsearch": "https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.16.1-windows-x86_64.zip",
}


def download(name, url):
    ROOT.mkdir(exist_ok=True)
    archive = ROOT / f"{name}.zip"
    if not archive.exists():
        print(f"Downloading {name} from its official distributor", flush=True)
        urllib.request.urlretrieve(url, archive)
    if name == "elasticsearch":
        expected = urllib.request.urlopen(url + ".sha512").read().decode().split()[0]
        with archive.open("rb") as file:
            actual = hashlib.file_digest(file, "sha512").hexdigest()
        if actual != expected:
            raise RuntimeError("Elasticsearch checksum mismatch")
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            if name == "postgres" and not member.filename.startswith(("pgsql/bin/", "pgsql/lib/", "pgsql/share/")):
                continue
            target = (ROOT / member.filename).resolve()
            if not target.is_relative_to(ROOT.resolve()):
                raise RuntimeError("Archive path escaped workspace runtime")
            package.extract(member, ROOT)
    print(f"{name} extracted", flush=True)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda pair: download(*pair), PACKAGES.items()))
