# Integração N8N ↔ Frappe LMS

> Documentação completa do workflow N8N "Kreativ API Ultimate" e como ele integra WhatsApp, Frappe LMS e Chatwoot.

---

## Visão Geral

O N8N funciona como **orquestrador central** entre todos os serviços:

```
WhatsApp → Evolution API → Typebot → N8N (webhook) → Frappe REST API
                                      ↓
                                 Chatwoot (transbordo humano)
                                      ↓
                                 PostgreSQL (pgvector/RAG bridge)
```

### Endpoint Principal

```
POST https://n8n.extensionista.site/webhook/kreativ-unified-api
Content-Type: application/json
```

---

## Ações Disponíveis (14 total)

O workflow unificado recebe `{ "phone": "55...", "action": "...", ... }` e roteia para o handler correto.

### Ações de Aluno

| Ação | Verbo/Endpoint Frappe | Descrição |
|------|----------------------|-----------|
| `check_student` | `GET /api/resource/LMS Enrollment?filters=...` | Verifica se telefone está cadastrado, retorna curso/módulo atual |
| `get_module` | `GET /api/resource/Course Lesson?filters=...` | Busca conteúdo do módulo atual (texto, vídeo, quiz) |
| `get_progress` | `GET /api/resource/LMS Enrollment?filters=...` | Retorna progresso, % concluído e certificados |
| `submit_quiz` | `POST /api/resource/LMS Quiz Submission` | Registra resposta do quiz |
| `enroll_student` | `POST /api/resource/LMS Enrollment` | Matricula aluno em um curso |
| `ai_tutor` | OpenRouter/DeepSeek | Tira dúvidas do aluno usando AI com contexto RAG |
| `emit_certificate` | `POST /api/method/lms.lms.utils.generate_certificate` | Gera certificado para aluno aprovado |
| `request_human` | Chatwoot API | **Transbordo humano** — transfere para atendente no Chatwoot |

### Ações RAG

| Ação | Destino | Descrição |
|------|---------|-----------|
| `rag_ingest` | PostgreSQL pgvector | Ingere conteúdo educacional para busca semântica |

### Ações Administrativas

| Ação | Descrição |
|------|-----------|
| `admin_upsert_student` | Criar/atualizar aluno (requer `course_id`) |
| `admin_reset_student` | Resetar progresso de um aluno |
| `admin_upsert_course` | Criar/atualizar curso (requer `name`) |
| `admin_upsert_module` | Criar/atualizar módulo (requer `course_id`, `module_number`, `title`) |
| `admin_upload_module_file` | Upload de arquivo para módulo (requer `module_id`, `file_base64`, `file_name`) |

---

## Configuração N8N

### Docker Compose

```yaml
n8n:
  image: n8nio/n8n:latest
  container_name: kreativ_n8n
  environment:
    N8N_HOST: n8n.extensionista.site
    WEBHOOK_URL: https://n8n.extensionista.site
    DB_TYPE: postgresdb
    DB_POSTGRESDB_HOST: kreativ_postgres
    DB_POSTGRESDB_DATABASE: ${POSTGRES_DB}
    N8N_AI_ENABLED: "true"
    N8N_COMMUNITY_PACKAGES_ENABLED: "true"
    NODE_FUNCTION_ALLOW_BUILTIN: "*"
    NODE_FUNCTION_ALLOW_EXTERNAL: "*"
    NODE_OPTIONS: "--max-old-space-size=2048"
```

### Variáveis de Ambiente Necessárias

| Variável | Uso |
|----------|-----|
| `FRAPPE_API_KEY` | Autenticação na API Frappe |
| `FRAPPE_API_SECRET` | Autenticação na API Frappe |
| `FRAPPE_LMS_URL` | URL base do Frappe LMS |
| `EVOLUTION_API_KEY` | Enviar mensagens WhatsApp |
| `OPEN_ROUTER_API` | AI tutor (DeepSeek/Gemini via OpenRouter) |
| `CHATWOOT_API_KEY` | Criar conversa de transbordo |

---

## Fluxo `request_human` (Transbordo)

O transbordo humano funciona assim:

```
1. Aluno digita "falar com humano" no WhatsApp
2. Typebot detecta intenção → chama N8N com action: "request_human"
3. N8N:
   a. Registra na tabela `handoff_control` (phone, status='human')
   b. Cria/reativa conversa no Chatwoot via API
   c. Notifica atendente no Chatwoot
   d. Responde ao aluno: "Aguarde, um atendente vai te ajudar"
4. Atendente responde via Chatwoot → Evolution API → WhatsApp
5. Atendente encerra atendimento:
   a. N8N atualiza `handoff_control` (status='bot')
   b. Bot retoma o controle da conversa
```

### Tabela `handoff_control` (PostgreSQL)

```sql
CREATE TABLE IF NOT EXISTS handoff_control (
    phone       VARCHAR(20) PRIMARY KEY,
    status      VARCHAR(10) DEFAULT 'bot',  -- 'bot' ou 'human'
    chatwoot_id INTEGER,
    updated_at  TIMESTAMP DEFAULT NOW()
);
```

### API Chatwoot usada pelo N8N

```bash
# Criar conversa
POST https://suporte.extensionista.site/api/v1/accounts/{account_id}/conversations
Authorization: Bearer {CHATWOOT_API_KEY}
{
  "source_id": "5563XXXXXXXX",
  "inbox_id": 1,
  "contact_id": 123,
  "status": "open"
}

# Enviar mensagem pelo agente
POST .../conversations/{conversation_id}/messages
{
  "content": "Olá, como posso ajudar?",
  "message_type": "outgoing"
}
```

---

## Bridge Phone → Email

Alunos acessam via WhatsApp (telefone). Frappe identifica users por email.

**Conversão padrão:** `55639937XXXX` → `55639937XXXX@aluno.kreativ.edu.br`

**Tabela bridge (PostgreSQL):**

```sql
SELECT * FROM student_frappe_map WHERE phone = '5563XXXXXXXX';
-- Retorna: frappe_email = '5563XXXXXXXX@aluno.kreativ.edu.br'
```

O N8N consulta esta tabela antes de qualquer chamada ao Frappe para resolver o `member` (email).

---

## Payload de Exemplo (Typebot → N8N)

```json
{
  "phone": "5563993712345",
  "action": "get_module",
  "course_id": 1,
  "module_number": 2
}
```

**Resposta N8N → Typebot:**

```json
{
  "success": true,
  "module": {
    "title": "Receita, custo, despesa e lucro",
    "content_summary": "Entendendo os termos financeiros...",
    "video_url": "https://lms.extensionista.site/lms/course/.../lesson/...",
    "has_quiz": true
  }
}
```

---

## Workflows N8N

| Arquivo | ID | Descrição |
|---------|-----|-----------|
| `60-kreativ-api-ultimate-frappe.json` | Workflow principal | Unified API com 14 ações |
| `70-wpp-conversation-engine.json` | Conversation Engine | Motor de conversa WhatsApp |

> Importe via N8N UI: **Settings → Import Workflow → Upload JSON**

---

## Instruções para Agentes IA (via N8N MCP)

Este repositório foi construído para ser o ponto de partida **end-to-end** ("start to finish" deployment). A stack Docker já inclui (`docker/n8n/Dockerfile`) os pacotes da comunidade pré-instalados:
- `@n8n-nodes-evolution/evolution` (Evolution API V2)
- `n8n-nodes-chatwoot` (Chatwoot API)

### Como usar o MCP para otimizar os fluxos

Como assistente de IA conectado ao MCP do N8N (`n8n-mcp`), você deve seguir este protocolo ao criar ou melhorar estes conectores:

1. **Evite `HTTP Request` Cru onde possível:** 
   O código legado de 2025 usava mais de 30 blocos `HTTP Request` para Chatwoot e Evolution. Isso gera JSONs de workflow frágeis.
2. **Descubra as Propridades dos Nós:**
   Em vez de adivinhar parâmetros para Chatwoot ou Evolution, use a tool de MCP `mcp_n8n-mcp_get_node` com `mode='docs'` ou `detail='full'`.
   Exemplo prático de tool call:
   `mcp_n8n-mcp_get_node(nodeType="n8n-nodes-chatwoot.chatwoot", mode="docs")`
3. **Migração do Transbordo Lógico:**
   O fluxo `request_human` listado acima deve ser reconstruído nos novos layouts usando os nós específicos:
   - Em vez de fazer PUT/POST manual: use o node `n8n-nodes-chatwoot.chatwoot` com a action `conversation` -> `create`.
4. **Validando os Configs:**
   Sempre use a tool `mcp_n8n-mcp_validate_node` passando o `nodeType` recém descoberto e o `config` pretendido em `mode="full"` antes de exportar o workflow.
   Isso garantirá que o JSON a ser gerado funcionará perfeitamente quando o humano fizer o "Import Workflow" na UI.

---

*Última atualização: 2026-03-04*
