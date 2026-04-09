# TDS - Arquitetura 2026

## Visao Geral

```
  WhatsApp (aluno)
       |
       v
  Chatwoot (chat.ipexdesenvolvimento.cloud)
       |
       v (webhook)
  N8N Workflow (n8n.ipexdesenvolvimento.cloud)
       |
       +--> PostgreSQL student_frappe_map (lookup telefone -> curso)
       |
       v (workspace dinamico)
  AnythingLLM RAG (rag.ipexdesenvolvimento.cloud)
       |  workspace por curso: tds-agricultura, tds-audiovisual, etc.
       |  cartilhas embedadas por workspace
       v
  Resposta ao aluno via Chatwoot
       |
  Frappe LMS (lms.ipexdesenvolvimento.cloud)
       |  7 cursos, 26 capitulos, 61 licoes
       |  Conteudo das cartilhas TDS
       v
  OpenClaw/Ollama (openclaw.ipexdesenvolvimento.cloud)
       |  Modelos: qwen2.5-coder:7b (local)
       |  Cloud: gpt-oss:120b, qwen3-coder:480b, deepseek-v3.1:671b
       |  Novo: gemma4:31b-cloud (pendente auth)
```

## Servicos Docker

| Container | Servico | Porta |
|-----------|---------|-------|
| kreativ-frappe-frontend | Frappe LMS frontend | 8080 |
| kreativ-backend | Frappe backend API | 8000 |
| kreativ-worker-* | Frappe workers (3) | - |
| kreativ-scheduler | Frappe scheduler | - |
| kreativ-socketio | Frappe realtime | - |
| kreativ-rag | AnythingLLM | 3001 |
| kreativ-ollama | Ollama | 11434 |
| kreativ-chatwoot | Chatwoot | 3000 |
| kreativ-n8n | N8N | 5678 |
| kreativ-postgres | PostgreSQL | 5432 |
| kreativ-redis | Redis | 6379 |
| kreativ-mariadb | MariaDB (Frappe) | 3306 |
| kreativ-mail | Poste.io | 25/443 |

## Fluxo de Dados

### 1. Mensagem WhatsApp -> RAG

1. Aluno envia mensagem no WhatsApp
2. Chatwoot recebe via Chatwoot API
3. Webhook dispara para N8N
4. N8N extrai telefone do contato
5. Busca na `student_frappe_map` -> encontra `rag_workspace`
6. Chama AnythingLLM `/api/v1/workspace/{slug}/chat`
7. RAG responde com base na cartilha do curso do aluno
8. N8N posta resposta no Chatwoot -> WhatsApp

### 2. Importacao de Alunos

1. CSV com dados SISEC/MDS
2. Script `import_students.py` processa:
   - Cria User no Frappe
   - Cria LMS Enrollment
   - Adiciona ao LMS Batch
   - Insere em `student_frappe_map`
3. Aluno automaticamente roteado para workspace correto

### 3. Credenciais

- Frappe API: token 056681de29fce7a:7c78dcba6e3c5d1
- AnythingLLM: Bearer W5M4VV3-DVQMN22-M2QF6JE-R5KFJP0
- PostgreSQL: kreativ@kreativ_edu (via docker exec)

## Tutores

| Tutor | Email | Cursos |
|-------|-------|--------|
| Valentine | valentine@ipexdesenvolvimento.cloud | Agricultura Sustentavel |
| Pedro H. | pedroh@ipexdesenvolvimento.cloud | Audiovisual |
| Gabriela | gabriela@ipexdesenvolvimento.cloud | Financas, Financas Melhor Idade |
| Sofia | sofia@ipexdesenvolvimento.cloud | Associativismo |
| Rafael | rafael@ipexdesenvolvimento.cloud | IA no meu Bolso |
| Sahaa | sahaa@ipexdesenvolvimento.cloud | SIM |
