import subprocess
import sys
import time

while True:
    print("Executing secrets provisioning...", flush=True)

    subprocess.run(
        [sys.executable, "/app/scripts/provision_secrets.py", "--apply"],
        check=False,
    )

    print("Next execution in 30 seconds.", flush=True)
    time.sleep(30)