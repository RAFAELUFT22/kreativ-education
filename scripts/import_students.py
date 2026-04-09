#!/usr/bin/env python3
"""
TDS — Kreativ Education: Importação de Alunos em Lote
Importa alunos de CSV/Excel para Frappe LMS + PostgreSQL bridge table.

Uso:
    python3 import_students.py alunos.csv
    python3 import_students.py --dry-run alunos.csv

CSV esperado (separador ; ou ,):
    nome_completo;cpf;telefone_celular;email;municipio;curso;turma;cadunico;
    genero;etnico_racial;data_nascimento;escolaridade;deficiencia;...

O script faz:
1. Cria User no Frappe (email = cpf@tds.edu.br ou email real)
2. Cria LMS Enrollment (matrícula no curso)
3. Adiciona ao LMS Batch (turma)
4. Insere na tabela student_frappe_map (PostgreSQL bridge para N8N)
"""

import csv
import json
import os
import re
import sys
import time
import requests
import subprocess

# ─── CONFIG ───────────────────────────────────────────────────────
FRAPPE_URL = "https://lms.ipexdesenvolvimento.cloud"
API_KEY = "056681de29fce7a"
API_SECRET = "7c78dcba6e3c5d1"
AUTH = f"token {API_KEY}:{API_SECRET}"
HEADERS = {
    "Authorization": AUTH,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

PG_CONTAINER = "kreativ-postgres"
PG_USER = "kreativ"
PG_DB = "kreativ_edu"

# Mapping de curso → slug do LMS Course e workspace RAG
COURSE_MAP = {
    "agricultura": {
        "lms_search": "agricultura",
        "rag_workspace": "tds-agricultura-sustentavel",
        "batch": "turma-tds-agricultura-sustent-vel-2026",
    },
    "audiovisual": {
        "lms_search": "audiovisual",
        "rag_workspace": "tds-audiovisual-e-conteudo",
        "batch": "turma-tds-audiovisual-e-conte-do-digital-2026",
    },
    "financas": {
        "lms_search": "finan",
        "rag_workspace": "tds-financas-e-empreendedorismo",
        "batch": "turma-tds-finan-as-e-empreendedorismo-2026",
    },
    "financas_idade": {
        "lms_search": "melhor-idade",
        "rag_workspace": "tds-educacao-financeira-terceira-idade",
        "batch": None,  # No batch created for this yet
    },
    "associativismo": {
        "lms_search": "associativismo",
        "rag_workspace": "tds-associativismo-e-cooperativismo",
        "batch": "turma-tds-associativismo-e-cooperativismo-2026",
    },
    "ia": {
        "lms_search": "ia-no-meu-bolso",
        "rag_workspace": "tds-ia-no-meu-bolso",
        "batch": "turma-tds-ia-no-meu-bolso-2026",
    },
    "sim": {
        "lms_search": "sim",
        "rag_workspace": "tds-sim",
        "batch": "turma-tds-sim-e-inspe-o-alimentar-2026",
    },
}


# ─── HELPERS ──────────────────────────────────────────────────────

def api_get(endpoint, params=None):
    url = f"{FRAPPE_URL}/api/resource/{endpoint}"
    r = requests.get(url, headers=HEADERS, params=params or {})
    r.raise_for_status()
    return r.json()

def api_post(endpoint, data):
    url = f"{FRAPPE_URL}/api/resource/{endpoint}"
    r = requests.post(url, headers=HEADERS, json=data)
    return r

def pg_exec(sql):
    """Execute SQL via docker exec."""
    cmd = [
        "docker", "exec", PG_CONTAINER,
        "psql", "-U", PG_USER, "-d", PG_DB,
        "-t", "-A", "-c", sql
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  PG ERROR: {result.stderr}")
    return result.stdout.strip()

def normalize_phone(phone):
    """Normalize phone to 55XXXXXXXXXXX format."""
    phone = re.sub(r'[^\d]', '', phone)
    if len(phone) == 11:  # DDD + number
        phone = "55" + phone
    elif len(phone) == 10:  # DDD + old format
        phone = "55" + phone
    elif not phone.startswith("55"):
        phone = "55" + phone
    return phone

def normalize_cpf(cpf):
    """Remove formatting from CPF."""
    return re.sub(r'[^\d]', '', cpf)

def find_course_slug(course_key):
    """Find the actual LMS Course slug for a course key."""
    if course_key not in COURSE_MAP:
        return None
    search = COURSE_MAP[course_key]["lms_search"]
    try:
        result = api_get("LMS Course", {
            "filters": json.dumps([["name", "like", f"%{search}%"]]),
            "fields": json.dumps(["name"]),
            "limit_page_length": 5,
            "order_by": "creation desc",
        })
        if result["data"]:
            return result["data"][0]["name"]
    except Exception as e:
        print(f"  Error finding course: {e}")
    return None

def detect_course_key(course_name):
    """Map user-provided course name to internal key."""
    name = course_name.lower().strip()
    if "agric" in name or "saf" in name or "agroflorestal" in name:
        return "agricultura"
    if "audiovisual" in name or "vídeo" in name or "video" in name:
        return "audiovisual"
    if "melhor idade" in name or "terceira idade" in name or "idoso" in name:
        return "financas_idade"
    if "finan" in name or "empreende" in name:
        return "financas"
    if "associativismo" in name or "cooperativismo" in name:
        return "associativismo"
    if "ia " in name or "inteligência artificial" in name or "inteligencia" in name:
        return "ia"
    if "sim " in name or "inspeção" in name or "inspecao" in name or "sima" in name:
        return "sim"
    return None


# ─── IMPORT PIPELINE ─────────────────────────────────────────────

def create_frappe_user(row):
    """Create a User in Frappe for the student."""
    cpf = normalize_cpf(row.get("cpf", ""))
    email = row.get("email", "").strip()
    nome = row.get("nome_completo", "").strip()

    # Generate email if not provided
    if not email:
        if cpf:
            email = f"{cpf}@tds.edu.br"
        else:
            # Use phone as fallback
            phone = normalize_phone(row.get("telefone_celular", ""))
            email = f"{phone}@tds.edu.br"

    # Split name
    parts = nome.split(maxsplit=1)
    first_name = parts[0] if parts else "Aluno"
    last_name = parts[1] if len(parts) > 1 else ""

    # Check if user exists
    try:
        api_get(f"User/{email}")
        print(f"    User already exists: {email}")
        return email
    except Exception:
        pass

    # Create user
    user_data = {
        "doctype": "User",
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "enabled": 1,
        "new_password": f"TDS@{cpf[-4:]}" if len(cpf) >= 4 else "TDS@2026",
        "roles": [
            {"role": "LMS Student"},
        ],
    }

    r = api_post("User", user_data)
    if r.status_code >= 400:
        if "already registered" in r.text.lower() or "duplicate" in r.text.lower():
            print(f"    User already exists: {email}")
            return email
        print(f"    ERROR creating user {email}: {r.status_code} {r.text[:200]}")
        return None

    print(f"    ✓ User created: {email}")
    return email


def enroll_student(email, course_slug):
    """Create LMS Enrollment for student."""
    r = api_post("LMS Enrollment", {
        "member": email,
        "course": course_slug,
    })
    if r.status_code >= 400:
        if "duplicate" in r.text.lower() or "already" in r.text.lower():
            print(f"    Enrollment exists: {email} → {course_slug}")
            return True
        print(f"    ERROR enrolling: {r.status_code} {r.text[:200]}")
        return False
    print(f"    ✓ Enrolled: {email} → {course_slug}")
    return True


def add_to_batch(email, batch_slug):
    """Add student to LMS Batch."""
    if not batch_slug:
        return False

    r = api_post("Batch Student", {
        "parent": batch_slug,
        "parenttype": "LMS Batch",
        "parentfield": "students",
        "student": email,
    })
    if r.status_code >= 400:
        if "duplicate" in r.text.lower():
            return True
        # Try alternative: update batch directly
        try:
            batch = api_get(f"LMS Batch/{batch_slug}")
            students = batch["data"].get("students", [])
            students.append({"student": email})
            requests.put(
                f"{FRAPPE_URL}/api/resource/LMS Batch/{batch_slug}",
                headers=HEADERS,
                json={"students": students}
            )
            print(f"    ✓ Added to batch: {batch_slug}")
            return True
        except Exception as e:
            print(f"    ERROR adding to batch: {e}")
            return False
    print(f"    ✓ Added to batch: {batch_slug}")
    return True


def insert_pg_bridge(row, email, course_slug, batch_slug, rag_workspace):
    """Insert into student_frappe_map PostgreSQL table."""
    phone = normalize_phone(row.get("telefone_celular", ""))
    cpf = normalize_cpf(row.get("cpf", ""))
    nome = row.get("nome_completo", "").replace("'", "''")
    municipio = row.get("municipio", row.get("cidade_uf", "")).replace("'", "''")
    cadunico = row.get("cadunico", "").strip().lower() in ("sim", "true", "1", "s")

    sql = f"""
    INSERT INTO student_frappe_map
        (phone_number, frappe_email, cpf, nome_completo, course_slug, batch_slug,
         rag_workspace, enrollment_date, cadunico, municipio)
    VALUES
        ('{phone}', '{email}', '{cpf}', '{nome}', '{course_slug}', '{batch_slug or ""}',
         '{rag_workspace or ""}', CURRENT_DATE, {cadunico}, '{municipio}')
    ON CONFLICT (phone_number) DO UPDATE SET
        frappe_email = EXCLUDED.frappe_email,
        course_slug = EXCLUDED.course_slug,
        batch_slug = EXCLUDED.batch_slug,
        rag_workspace = EXCLUDED.rag_workspace,
        updated_at = NOW();
    """
    pg_exec(sql)
    print(f"    ✓ PG bridge: {phone} → {rag_workspace}")


def import_student(row, dry_run=False):
    """Import a single student."""
    nome = row.get("nome_completo", "").strip()
    curso_input = row.get("curso", "").strip()

    if not nome:
        print("  SKIP: no name")
        return False

    course_key = detect_course_key(curso_input)
    if not course_key:
        print(f"  SKIP: unrecognized course '{curso_input}' for {nome}")
        return False

    course_info = COURSE_MAP[course_key]
    course_slug = find_course_slug(course_key)

    if not course_slug:
        print(f"  SKIP: course not found in LMS for key '{course_key}'")
        return False

    print(f"\n  Importing: {nome} → {course_key}")

    if dry_run:
        print(f"    [DRY RUN] Would create user, enroll in {course_slug}, add to {course_info['batch']}")
        return True

    # 1. Create Frappe User
    email = create_frappe_user(row)
    if not email:
        return False

    # 2. Enroll in course
    enroll_student(email, course_slug)

    # 3. Add to batch
    add_to_batch(email, course_info["batch"])

    # 4. Insert into PostgreSQL bridge
    insert_pg_bridge(
        row, email, course_slug,
        course_info["batch"],
        course_info["rag_workspace"]
    )

    time.sleep(0.3)
    return True


# ─── MAIN ─────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 import_students.py [--dry-run] <arquivo.csv>")
        print("\nCSV esperado (separador ; ou ,):")
        print("  nome_completo;cpf;telefone_celular;email;municipio;curso;turma;cadunico")
        print("\nExemplo de linha:")
        print('  Maria Silva;123.456.789-00;63999887766;maria@email.com;Palmas-TO;Agricultura;turma-agricultura;sim')
        sys.exit(1)

    dry_run = "--dry-run" in sys.argv
    csv_file = [a for a in sys.argv[1:] if not a.startswith("--")][0]

    if not os.path.exists(csv_file):
        print(f"Arquivo não encontrado: {csv_file}")
        sys.exit(1)

    print("=" * 60)
    print("TDS — Importação de Alunos")
    print("=" * 60)

    if dry_run:
        print("  *** MODO DRY RUN — nenhuma alteração será feita ***")

    # Detect CSV separator
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        first_line = f.readline()
        separator = ";" if ";" in first_line else ","

    # Read CSV
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=separator)
        rows = list(reader)

    print(f"\n  Arquivo: {csv_file}")
    print(f"  Alunos encontrados: {len(rows)}")
    print(f"  Separador: '{separator}'")
    print(f"  Colunas: {', '.join(rows[0].keys()) if rows else 'N/A'}")

    # Import
    success = 0
    errors = 0

    for i, row in enumerate(rows, 1):
        try:
            if import_student(row, dry_run=dry_run):
                success += 1
            else:
                errors += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"RESUMO: {success} importados, {errors} erros, {len(rows)} total")
    print("=" * 60)

    if not dry_run:
        # Show bridge table count
        count = pg_exec("SELECT COUNT(*) FROM student_frappe_map")
        print(f"\nTotal no student_frappe_map: {count} registros")


if __name__ == "__main__":
    main()
