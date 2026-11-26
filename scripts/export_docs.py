"""Exercise every documented operation, validate outputs, export reproducible Postman/OpenAPI."""

import argparse
import json
import re
import sys
import tempfile
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import jsonschema  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from scripts.demo import steps  # noqa: E402

DESCRIPTION = """API REST complète du sujet My Social Networks API v2.0.0.

Base locale : http://localhost:8000 ; préfixe métier : /api/v1.
Documentation interactive : /docs ; contrat OpenAPI : /openapi.json.

Inscription : POST /api/v1/users. Authentification : POST /api/v1/auth/login.
Copier access_token dans la variable token. Session Bearer valable 24 heures.
Les acheteurs sans compte utilisent X-Ticket-Token pour leur billet.

Toutes les listes acceptent q (recherche), limit (1 à 100, défaut 20) et offset (défaut 0).
Montants entiers en centimes EUR. Dates ISO 8601 avec fuseau horaire, réponses en UTC.
PUT remplace les champs modifiables. DELETE retourne 204 sans corps.
401 : session absente/invalide ; 403 : droits insuffisants ; 404 : ressource absente/inaccessible ;
409 : conflit métier/unicité/stock ; 422 : données invalides ; 429 : trop de tentatives.

Parcours : configuration de l'événement, options, publication.
Un participant invité doit accepter avant de publier, commenter ou voter.
Le dernier responsable d'un événement/groupe ne peut pas être retiré.
Les photos et couvertures sont des URL HTTP(S). Aucun fichier ni paiement bancaire n'est traité.
La billetterie enregistre l'obtention d'un billet et le montant associé.

La collection « Parcours complet » s'exécute dans l'ordre, crée des données fictives,
teste chaque réponse et supprime ses données. La collection « Référence » documente
toutes les opérations ; ses requêtes s'utilisent individuellement avec les identifiants adaptés.
Ne publier ni jeton personnel, ni environnement contenant de vraies coordonnées.
"""


def substitute(value, variables):
    if isinstance(value, dict):
        return {k: substitute(v, variables) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, variables) for v in value]
    if not isinstance(value, str):
        return value
    exact = re.fullmatch(r"\{\{(\w+)\}\}", value)
    if exact:
        return variables[exact[1]]
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(variables[m[1]]), value)


def scrub(value):
    if isinstance(value, list):
        return [scrub(v) for v in value]
    if isinstance(value, dict):
        output = {}
        for key, val in value.items():
            if key in {"access_token", "receipt_token"}:
                output[key] = "EXAMPLE_TOKEN_NOT_VALID"
            elif key in {"created_at", "purchased_at"}:
                output[key] = "2030-01-01T00:00:00.000Z"
            else:
                output[key] = scrub(val)
        return output
    return value


def run_journey():
    variables = {"run_id": "demo"}
    recordings = {}
    with tempfile.TemporaryDirectory() as directory:
        app = create_app(Path(directory) / "demo.db", rate_limit=False)
        with TestClient(app) as client:
            schema = app.openapi()
            for step in steps():
                path = substitute(step["path"], variables)
                headers = substitute(step["headers"], variables)
                if step["auth"]:
                    headers["Authorization"] = "Bearer " + variables[step["auth"]]
                kwargs = {"headers": headers}
                if step["body"] is not None:
                    kwargs["json"] = substitute(step["body"], variables)
                response = client.request(step["method"], path, **kwargs)
                if response.status_code != step["status"]:
                    raise AssertionError(f"{step['name']}: {response.status_code} {response.text}")
                route_path = next(
                    p
                    for p, methods in schema["paths"].items()
                    if step["method"].lower() in methods
                    and re.fullmatch(re.sub(r"\{[^}]+\}", "[^/]+", p), path.split("?")[0])
                )
                operation = schema["paths"][route_path][step["method"].lower()]
                output = response.json() if response.content else None
                if output is not None:
                    contract = operation["responses"][str(step["status"])]["content"]["application/json"][
                        "schema"
                    ]
                    jsonschema.validate(output, contract)
                else:
                    assert response.status_code == 204
                for variable, dotted_path in step["save"].items():
                    val = output
                    for part in dotted_path.split("."):
                        val = val[int(part)] if isinstance(val, list) else val[part]
                    variables[variable] = val
                recordings.setdefault((route_path, step["method"].lower()), (deepcopy(step), scrub(output)))
            expected = {(p, m) for p, methods in schema["paths"].items() for m in methods}
            missing = expected - recordings.keys()
            if missing:
                raise AssertionError(f"Operations without executable examples: {missing}")
            from app.db import connect

            with connect(app.state.database_path) as db:
                for table in ("users", "groups", "events", "tickets"):
                    assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
    return schema, recordings


def raw_body(body):
    raw = json.dumps(body, ensure_ascii=False, indent=2)
    # IDs must remain JSON numbers after Postman variable interpolation.
    return re.sub(r'"\{\{(\w+_id)\}\}"', r"{{\1}}", raw)


def make_item(step, operation, response, name=None):
    auth = (
        {
            "type": "bearer",
            "bearer": [{"key": "token", "value": "{{" + step["auth"] + "}}", "type": "string"}],
        }
        if step["auth"]
        else {"type": "noauth"}
    )
    response_schema = (
        operation["responses"]
        .get(str(step["status"]), {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    description = operation.get("description", operation["summary"])
    description += "\n\n" + f"Succès : HTTP {step['status']}. "
    if response_schema:
        description += "Données retournées (contrat JSON Schema) :\n\n" + json.dumps(
            response_schema, ensure_ascii=False, indent=2
        )
    else:
        description += "Aucun corps de réponse."
    description += "\n\nParamètres et validation : voir docs/openapi.json et /docs. Les erreurs communes sont décrites en introduction."
    request = {
        "method": step["method"],
        "header": [{"key": k, "value": v} for k, v in step["headers"].items()],
        "auth": auth,
        "url": "{{base_url}}" + step["path"],
        "description": description,
    }
    if step["body"] is not None:
        request["header"].append({"key": "Content-Type", "value": "application/json"})
        request["body"] = {
            "mode": "raw",
            "raw": raw_body(step["body"]),
            "options": {"raw": {"language": "json"}},
        }
    tests = [
        f"pm.test('HTTP {step['status']}', function () {{ pm.response.to.have.status({step['status']}); }});"
    ]
    if step["save"]:
        tests.append("var socialResponse = pm.response.json();")
        for key, path in step["save"].items():
            expression = "socialResponse" + "".join(
                f"[{json.dumps(p) if not p.isdigit() else p}]" for p in path.split(".")
            )
            tests.append(f"pm.collectionVariables.set({json.dumps(key)}, {expression});")
    item = {
        "name": name or operation["summary"],
        "request": request,
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": tests}}],
        "response": [
            {
                "name": f"Succès {step['status']}",
                "originalRequest": deepcopy(request),
                "status": {200: "OK", 201: "Created", 204: "No Content"}[step["status"]],
                "code": step["status"],
                "_postman_previewlanguage": "json",
                "header": [] if response is None else [{"key": "Content-Type", "value": "application/json"}],
                "body": "" if response is None else json.dumps(response, ensure_ascii=False, indent=2),
            }
        ],
    }
    return item


def outputs():
    schema, recordings = run_journey()
    reference_groups = defaultdict(list)
    by_signature = {}
    for (path, method), (step, response) in recordings.items():
        operation = schema["paths"][path][method]
        if response is not None:
            operation["responses"][str(step["status"])]["content"]["application/json"]["example"] = response
        item = make_item(step, operation, response)
        reference_groups[operation["tags"][0]].append(item)
        by_signature[(path, method)] = item
    variables = {"base_url": "http://localhost:8000", "run_id": "manual"}
    for step in steps():
        for name in re.findall(r"\{\{(\w+)\}\}", json.dumps(step)):
            variables.setdefault(name, "")
        for name in step["save"]:
            variables.setdefault(name, "")
        if step["auth"]:
            variables.setdefault(step["auth"], "")

    def collection(name, uid, items):
        return {
            "info": {
                "_postman_id": uid,
                "name": name,
                "description": DESCRIPTION,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "variable": [{"key": k, "value": v, "type": "string"} for k, v in sorted(variables.items())],
            "item": items,
        }

    reference = collection(
        "My Social Networks API v2.0.0 — Référence",
        "120dcb2c-58af-46b5-b04a-1d8017239619",
        [{"name": k, "item": v} for k, v in reference_groups.items()],
    )
    journey = []
    for number, step in enumerate(steps(), 1):
        normalized = re.sub(r"\{\{\w+\}\}", "1", step["path"]).split("?")[0]
        match = next(
            (p, m)
            for p, m in recordings
            if m == step["method"].lower() and re.fullmatch(re.sub(r"\{[^}]+\}", r"[^/]+", p), normalized)
        )
        operation = schema["paths"][match[0]][match[1]]
        journey.append(make_item(step, operation, recordings[match][1], f"{number:03d} — {step['name']}"))
    journey[0]["event"].insert(
        0,
        {
            "listen": "prerequest",
            "script": {
                "type": "text/javascript",
                "exec": [
                    "pm.collectionVariables.set('run_id', Date.now().toString() + Math.floor(Math.random()*100000).toString());"
                ],
            },
        },
    )
    scenario = collection(
        "My Social Networks API v2.0.0 — Parcours complet", "33536166-8c12-4519-bdbd-a5e25f89035d", journey
    )
    env = {
        "id": "f726b63e-d38e-4bf3-9bc7-f36f60164087",
        "name": "My Social Networks — Local",
        "values": [{"key": "base_url", "value": "http://localhost:8000", "enabled": True}],
        "_postman_variable_scope": "environment",
    }
    table = [
        "# Référence des endpoints",
        "",
        f"{len(recordings)} opérations HTTP vérifiées par le parcours complet.",
        "",
        "Base : http://localhost:8000. Les identifiants des parents sont immuables.",
        "",
        "| Méthode | URL | Fonction | Succès |",
        "|---|---|---|---|",
    ]
    for (path, method), (step, _) in recordings.items():
        table.append(
            f"| {method.upper()} | {path} | {schema['paths'][path][method]['summary']} | {step['status']} |"
        )
    table += [
        "",
        "Les descriptions détaillées, corps attendus et réponses JSON sont inclus dans la collection Postman et dans openapi.json.",
        "Les listes acceptent q, limit et offset ; certains services proposent aussi group_id ou event_id.",
        "Les paramètres parent_id et item_id désignent la ressource nommée dans le chemin (fil, album, photo, etc.).",
        "",
    ]
    files = {
        "docs/openapi.json": schema,
        "postman/My-Social-Networks.postman_collection.json": reference,
        "postman/Parcours-complet.postman_collection.json": scenario,
        "postman/Local.postman_environment.json": env,
    }
    rendered = {path: json.dumps(data, ensure_ascii=False, indent=2) + "\n" for path, data in files.items()}
    rendered["docs/ENDPOINTS.md"] = "\n".join(table)
    return rendered, len(recordings), len(journey)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true", help="Fail if exports are stale, without rewriting them"
    )
    args = parser.parse_args()
    files, operations, count = outputs()
    for path, content in files.items():
        target = ROOT / path
        if args.check:
            if not target.exists() or target.read_text() != content:
                raise SystemExit(f"Export obsolète : {path}. Exécutez python scripts/export_docs.py")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
    print(f"{operations} opérations documentées ; {count} étapes exécutées et réponses validées.")
