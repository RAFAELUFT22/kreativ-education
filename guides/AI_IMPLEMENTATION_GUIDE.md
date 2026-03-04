# AI Implementation Guide — Kreativ Education

> **Para:** Gemini, Claude, Cursor, Copilot ou qualquer assistente IA que for trabalhar neste repositório.
> Leia este documento inteiramente antes de fazer qualquer mudança.

---

## 🎯 Objetivo do Projeto

**Kreativ Education** é uma plataforma de educação conversacional que entrega cursos de empreendedorismo via **WhatsApp** para comunidades periféricas no Brasil. O Frappe LMS é o backbone acadêmico (cursos, matrículas, quizzes, certificados).

### Stack Tecnológico

| Componente | Tecnologia | Função |
|-----------|-----------|---------|
| **LMS** | Frappe LMS v2.44+ (Python/MariaDB) | Gestão de cursos, matrículas, quizzes |
| **Automação** | N8N (Node.js) | Lógica de negócio, pipeline WhatsApp→Frappe |
| **WhatsApp** | Evolution API v2 + Meta Cloud API | Canal de comunicação com alunos |
| **Bot Visual** | Typebot v6 | Fluxo conversacional visual |
| **RAG** | PostgreSQL + pgvector | Busca semântica em conteúdo educacional |
| **Infra** | Docker Compose + Traefik | Orquestração e SSL |

---

## 📐 Arquitetura

```
WhatsApp → Evolution API → Typebot → N8N → Frappe REST API
                                           ↓
                                     MariaDB (LMS)
                                     PostgreSQL (pgvector/RAG bridge)
```

### Princípio Fundamental

> **Frappe LMS = fonte da verdade acadêmica.**
> PostgreSQL retém APENAS pgvector (RAG) e a tabela `student_frappe_map` (bridge phone→email).
> Todo CRUD de cursos, matrículas, quizzes e certificados é feito via Frappe REST API.

---

## 🔑 Padrões de API Frappe

### Autenticação

```http
Authorization: token {API_KEY}:{API_SECRET}
Content-Type: application/json
```

### CRUD Básico

| Operação | HTTP | Endpoint |
|----------|------|----------|
| Criar | `POST` | `/api/resource/{DocType}` |
| Ler | `GET` | `/api/resource/{DocType}/{name}` |
| Listar | `GET` | `/api/resource/{DocType}?filters=...&fields=...` |
| Atualizar | `PUT` | `/api/resource/{DocType}/{name}` |
| Deletar | `DELETE` | `/api/resource/{DocType}/{name}` |

### Child Tables

Child tables são arrays de objetos dentro do JSON do documento pai:

```json
{
  "title": "Meu Curso",
  "instructors": [
    {"instructor": "admin@example.com"}
  ]
}
```

### Filtros

Formato: `filters=[["campo","operador","valor"]]`

```
?filters=[["published","=",1],["title","like","%gestão%"]]
```

---

## 📝 Fluxo de Criação de Curso

**Ordem obrigatória** (dependências):

1. `LMS Course` → retorna `course_name`
2. `Course Chapter` → usa `course_name`, retorna `chapter_name`
3. `Course Lesson` → usa `chapter_name` + `course_name`
4. `LMS Quiz` → independente, retorna `quiz_name`
5. `LMS Question` → independente, retorna `question_name`
6. Vincular quiz → `PUT Course Lesson/{name}` com `quiz_id`

> 📖 Veja `docs/COURSE_CREATION_API.md` para referência completa com exemplos curl.

---

## 🧭 Convenções de Nomes

### DocTypes do LMS (principais)

| DocType | Descrição |
|---------|-----------|
| `LMS Course` | Curso |
| `Course Chapter` | Capítulo |
| `Course Lesson` | Lição |
| `LMS Quiz` | Quiz |
| `LMS Question` | Pergunta |
| `LMS Option` | Opção de resposta |
| `LMS Enrollment` | Matrícula |
| `LMS Certificate` | Certificado |
| `LMS Batch` | Turma |
| `LMS Category` | Categoria |
| `LMS Assignment` | Tarefa |
| `LMS Assessment` | Avaliação |
| `LMS Course Progress` | Progresso por lição |

### Naming Convention

- URLs usam URL encoding: `LMS Course` → `LMS%20Course`
- `name` fields são slugs gerados automaticamente: `"Gestão Financeira"` → `"gestao-financeira"`

---

## ⚠️ Gotchas & Problemas Conhecidos

### 1. OOM no `bench build` (Critical)

O frontend Vue do LMS compila **3885 módulos** via vite e precisa de **~2GB heap JS**.
O container backend DEVE ter **pelo menos 4GB de RAM**:

```bash
# Se o build falhar com exit code 137 ou 134:
docker update --memory 4g --memory-swap 6g kreativ_frappe_backend
docker exec kreativ_frappe_backend bench build --app lms
```

### 2. CORS para chamadas externas

Configurar no Frappe:
```bash
bench --site SITE set-config allow_cors 1
bench --site SITE set-config cors_origin '*'
```

### 3. `bench migrate` após mudanças

Sempre execute após instalar apps ou atualizar schema:
```bash
docker exec kreativ_frappe_backend bench --site SITE migrate
```

### 4. Alunos precisam ser Users

Para matricular via API, o aluno precisa existir como `User` no Frappe:
```bash
curl -X POST ".../api/resource/User" -d '{"email":"aluno@email.com","first_name":"João","enabled":1}'
```

### 5. Child table via API

Para adicionar questões a um quiz **existente**, use o endpoint do pai:
```json
PUT /api/resource/LMS Quiz/{name}
{"questions": [{"question": "QUESTION-NAME", "marks": 1}]}
```

---

## 📁 Estrutura do Repositório

```
kreativ-education/
├── docker/          → Infraestrutura Docker (Dockerfile, compose)
├── scripts/         → Automação (setup, build, seed, health)
├── docs/            → Documentação técnica completa
├── guides/          → Este guia + contexto de negócio
├── courses/         → Templates JSON + dados TDS reais
├── n8n-workflows/   → Workflows N8N relevantes
└── init-scripts/    → SQL migrations (bridge PG)
```

---

## 📚 Documentação de Referência

| Documento | O que contém |
|-----------|-------------|
| `docs/COURSE_CREATION_API.md` | Como criar cursos+quiz via API (exemplos completos) |
| `docs/ARCHITECTURE.md` | Diagrama e explicação de cada componente |
| `docs/DEPLOYMENT_GUIDE.md` | Passo a passo para deploy em VPS nova |
| `docs/CAPACITY_PLANNING.md` | Requisitos de RAM/CPU por serviço |
| `docs/TROUBLESHOOTING.md` | Problemas comuns e soluções |
| `guides/KREATIV_CONTEXT.md` | Contexto de negócio TDS/Kreativ |
| `guides/CODING_CONVENTIONS.md` | Padrões de código |

---

## 🔄 Integração N8N ↔ Frappe

O workflow N8N "Kreativ API Ultimate" chama o Frappe via 6 ações:

| Ação N8N | Verbo | Endpoint Frappe |
|----------|-------|-----------------|
| `check_student` | GET | `/api/resource/LMS Enrollment?filters=...` |
| `get_module` | GET | `/api/resource/Course Lesson?filters=...` |
| `get_progress` | GET | `/api/resource/LMS Enrollment?filters=...` |
| `submit_quiz` | POST | `/api/resource/LMS Quiz Submission` |
| `emit_certificate` | POST | `/api/method/lms.lms.utils.generate_certificate` |
| `enroll_student` | POST | `/api/resource/LMS Enrollment` |

### 🤖 Diretrizes MCP (Para Agentes de IA)

Para modificar os workflows N8N, aja segundo este protocolo:
1. **O Docker é Customizado:** A imagem `kreativ_n8n` não é stock. Usamos `docker/n8n/Dockerfile` para pré-instalar pacotes `n8n-nodes-evolution` e `n8n-nodes-chatwoot`.
2. **Use Tooling do MCP:** NUNCA crie automações com nós *HTTP Request* genéricos para WhatsApp ou Chatwoot.
3. **Descubra as Estruturas:** Como IA, use `mcp_n8n-mcp_get_node(nodeType="...", mode="docs")` para aprender como usar os nós comunitários instalados.
4. **Valide:** Valide seus workflows via `mcp_n8n-mcp_validate_workflow` ANTES de entregar o JSON pro usuário.
Veja as instruções detalhadas e lista de 14 ações na doc inteira (`docs/N8N_INTEGRATION.md`).

### Bridge Phone → Email

Alunos acessam via WhatsApp (telefone). No Frappe, usuários são identificados por email.
A conversão: `55639937XXXX` → `55639937XXXX@aluno.kreativ.edu.br`

---

*Última atualização: 2026-03-04*
