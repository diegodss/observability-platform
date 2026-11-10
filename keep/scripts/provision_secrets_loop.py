import subprocess
import sys
import time

while True:
    print("Executando provisionamento de secrets...", flush=True)

    subprocess.run(
        [sys.executable, "/app/scripts/provision_secrets.py", "--apply"],
        check=False,
    )

    print("Próxima execução em 30 segundos.", flush=True)
    time.sleep(30)