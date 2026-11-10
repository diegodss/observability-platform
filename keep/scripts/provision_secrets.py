
import argparse
import json
import os
import tempfile
from pathlib import Path

import yaml
from sqlmodel import Session, select

from keep.api.core.db import engine
from keep.api.models.db.workflow import Workflow


WORKFLOWS_DIR = Path("/app/workflows")
CONFIG_DIR = Path("/app/secrets-config")
SECRET_DIR = Path(os.environ.get("SECRET_MANAGER_DIRECTORY", "/secret"))
TENANT = "keep"


def read_env(path):
    result = {}
    if not path.exists():
        return result

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].strip()

        key, sep, value = line.partition("=")
        if not sep:
            continue

        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]

        if key:
            result[key] = value

    return result


def load_yaml_id(content):
    data = yaml.safe_load(content) or {}

    if isinstance(data.get("workflow"), dict):
        data = data["workflow"]

    return data.get("id")


def atomic_write(path, content):
    if path.exists() and path.read_text() == content:
        return False

    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        return True
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Grava as secrets. Sem esta opção, apenas simula.",
    )
    args = parser.parse_args()

    global_secrets = read_env(CONFIG_DIR / "global.env")

    if not global_secrets:
        raise SystemExit("ERRO: global.env está vazio.")

    yaml_ids = {}

    for path in list(WORKFLOWS_DIR.glob("*.yaml")) + list(WORKFLOWS_DIR.glob("*.yml")):
        logical_id = load_yaml_id(path.read_text())
        if not logical_id:
            print(f"AVISO: YAML sem id: {path.name}")
            continue

        if logical_id in yaml_ids:
            raise SystemExit(f"ERRO: ID lógico duplicado: {logical_id}")

        yaml_ids[logical_id] = path

    with Session(engine) as session:
        workflows = session.exec(
            select(Workflow).where(
                Workflow.tenant_id == TENANT,
                Workflow.is_deleted == False,
            )
        ).all()

        matched = {}

        for workflow in workflows:
            logical_id = load_yaml_id(workflow.workflow_raw)

            if logical_id in yaml_ids:
                if logical_id in matched:
                    raise SystemExit(f"ERRO: ID duplicado no banco: {logical_id}")
                matched[logical_id] = workflow

    missing = set(yaml_ids) - set(matched)
    if missing:
        raise SystemExit(
            "ERRO: workflows ainda não encontrados no banco: "
            + ", ".join(missing)
            + ". Reinicie o backend e tente novamente."
        )

    for logical_id, workflow in matched.items():
        local_file = CONFIG_DIR / "workflows" / f"{logical_id}.env"
        local_secrets = read_env(local_file)

        secret_file = SECRET_DIR / f"{TENANT}_{workflow.id}_secrets"

        existing = {}
        if secret_file.exists():
            existing = json.loads(secret_file.read_text())
            if not isinstance(existing, dict):
                raise SystemExit(f"ERRO: JSON inválido em {secret_file.name}")

        # Precedência: existentes < globais < individuais.
        merged = {
            str(k).strip(): v
            for k, v in existing.items()
        }
        merged.update(global_secrets)
        merged.update(local_secrets)

        print(f"\nWorkflow: {logical_id}")
        print(f"UUID atual: {workflow.id}")
        print(f"Arquivo: {secret_file.name}")
        print(f"Chaves: {sorted(merged.keys())}")

        if args.apply:
            SECRET_DIR.mkdir(parents=True, exist_ok=True)
            changed = atomic_write(
                secret_file,
                json.dumps(merged, ensure_ascii=False, indent=2),
            )
            print("GRAVADO" if changed else "SEM ALTERAÇÃO")
        else:
            print("SIMULAÇÃO: nenhuma alteração realizada.")

    print("\nConcluído.")


if __name__ == "__main__":
    main()
