"""Start isolated, loopback-only services without changing installed system services."""
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import time
from urllib.request import urlopen
from urllib.parse import quote

PROJECT = Path(__file__).resolve().parents[3]
RUNTIME = PROJECT / ".runtime"
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def secret_file(name):
    path = RUNTIME / name
    if not path.exists():
        path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def environment():
    RUNTIME.mkdir(exist_ok=True)
    env = os.environ.copy()
    env.update(DATABASE_URL=f"postgresql+asyncpg://darktrace:{quote(secret_file('postgres.password'))}@127.0.0.1:15432/darktracex", ELASTICSEARCH_URL="http://127.0.0.1:19200", JWT_SECRET=secret_file("jwt.key"), CORS_ORIGINS="http://localhost:3000,http://127.0.0.1:3000", PYTHONUNBUFFERED="1")
    return env


def listening(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def run(args, env=None):
    result = subprocess.run([str(a) for a in args], env=env, capture_output=True, creationflags=FLAGS)
    if result.returncode:
        # Service initialization errors contain paths and configuration, never passwords.
        raise RuntimeError(f"{Path(args[0]).name} exited {result.returncode}: {result.stderr.decode(errors='replace')[-1500:]}")
    return result.stdout


def wait_ready(url, name, timeout=45):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError(f"{name} did not become ready; inspect .runtime logs")


def start():
    env = environment()
    pg = RUNTIME / "pgsql" / "bin"
    data = RUNTIME / "postgres-data"
    if not (data / "PG_VERSION").exists():
        run([pg/"initdb.exe", "-D", data, "-U", "darktrace", "--pwfile", RUNTIME/"postgres.password", "--auth=scram-sha-256", "-E", "UTF8", "--locale=C"])
    if not listening(15432):
        # A detached PostgreSQL process can retain inherited pipe handles on Windows.
        # Use files instead of PIPE so the launcher can finish after pg_ctl exits.
        with (RUNTIME/"postgres-launch.log").open("ab") as log:
            subprocess.run([str(pg/"pg_ctl.exe"), "-D", str(data), "-l", str(RUNTIME/"postgres.log"), "-o", "-p 15432 -h 127.0.0.1", "-w", "-t", "30", "start"], stdout=log, stderr=log, creationflags=FLAGS, check=True, timeout=45)
    pg_env = {**env, "PGPASSWORD": secret_file("postgres.password")}
    exists = run([pg/"psql.exe", "-h", "127.0.0.1", "-p", "15432", "-U", "darktrace", "-d", "postgres", "-tAc", "SELECT 1 FROM pg_database WHERE datname='darktracex'"], pg_env)
    if not exists.strip():
        run([pg/"createdb.exe", "-h", "127.0.0.1", "-p", "15432", "-U", "darktrace", "darktracex"], pg_env)
    print("PostgreSQL ready on loopback:15432", flush=True)
    es = RUNTIME / "elasticsearch-8.16.1"
    if not listening(19200):
        (es/"config"/"elasticsearch.yml").write_text("cluster.name: darktracex-local\nnode.name: local-1\nnetwork.host: 127.0.0.1\nhttp.port: 19200\ntransport.port: 19300\ndiscovery.type: single-node\nxpack.security.enabled: false\nxpack.ml.enabled: false\n", encoding="utf-8")
        log = (RUNTIME/"elasticsearch.log").open("ab")
        subprocess.Popen(["cmd.exe", "/d", "/c", str(es/"bin"/"elasticsearch.bat")], cwd=es, env={**env, "ES_JAVA_OPTS":"-Xms512m -Xmx512m"}, stdout=log, stderr=log, creationflags=FLAGS)
        log.close()
    print("Elasticsearch starting on loopback:19200", flush=True)
    for _ in range(60):
        if listening(19200):
            break
        time.sleep(1)
    if not listening(8000):
        log=(RUNTIME/"api.log").open("ab")
        subprocess.Popen([str(PROJECT/"apps/api/.venv313/Scripts/python.exe"), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=PROJECT/"apps/api", env=env, stdout=log, stderr=log, creationflags=FLAGS)
        log.close()
    wait_ready("http://127.0.0.1:8000/api/v1/health/ready", "API")
    if not listening(3000):
        log=(RUNTIME/"web.log").open("ab")
        subprocess.Popen([shutil.which("node"), str(PROJECT/"apps/web/node_modules/next/dist/bin/next"), "start", "-H", "127.0.0.1", "-p", "3000"], cwd=PROJECT/"apps/web", env=env, stdout=log, stderr=log, creationflags=FLAGS)
        log.close()
    wait_ready("http://127.0.0.1:3000", "Dashboard")
    print("Dashboard ready at http://localhost:3000", flush=True)


if __name__ == "__main__":
    start()
