# Dicionário de APIs dos Containers Docker

> Mapeamento completo de como acessar e interagir com as APIs de cada serviço rodando na arquitetura do Kreativ Education (LMS + WhatsApp Stack).

---

## 1. Frappe LMS (Educação)

O Frappe Framework possui uma REST API auto-gerada para todos os DocTypes.

- **Container:** `kreativ_frappe_backend`, `kreativ_frappe_frontend`
- **URL Base Externa:** `https://lms.extensionista.site`
- **URL Base Interna (Docker):** `http://kreativ_frappe_frontend:8080`
- **Autenticação:** Header `Authorization: token {API_KEY}:{API_SECRET}`
- **Formato:** JSON

### Endpoints Principais
| Verbo | Endpoint | Descrição |
|-------|----------|-----------|
| `GET` | `/api/resource/{DocType}` | Listar registros (suporta `?filters=[["ano","=",2026]]`) |
| `POST`| `/api/resource/{DocType}` | Criar registro (body em JSON) |
| `GET` | `/api/resource/{DocType}/{name}` | Ler 1 registro específico |
| `PUT` | `/api/resource/{DocType}/{name}` | Atualizar registro |
| `POST`| `/api/method/{app.module.method}`| Executar método Python arbitrário (RPC) |

> 📖 **Guia Profundo:** Veja `docs/COURSE_CREATION_API.md` para campos exatos de Cursos e Lições.

---

## 2. Evolution API (WhatsApp)

Motor de mensageria conectando-se à API Oficial do WhatsApp (Meta Cloud API).

- **Container:** `kreativ_evolution`
- **URL Base Externa:** `https://evolution.extensionista.site`
- **URL Base Interna (Docker):** `http://kreativ_evolution:8080`
- **Autenticação:** Header `apikey: {EVOLUTION_API_KEY}`
- **Docs:** `https://evolution.extensionista.site/docs` (Swagger UI)

### Endpoints Principais
| Verbo  | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/message/sendText/{instancia}` | Envia mensagem de texto |
| `POST` | `/message/sendMedia/{instancia}`| Envia imagem, vídeo ou PDF |
| `POST` | `/message/sendButtons/{instancia}`| Envia botões interativos (só funciona com Meta API) |
| `GET`  | `/instance/connectionState/{instancia}` | Verifica status da conexão |

---

## 3. N8N (Automação Webhooks)

O orquestrador. As APIs ativas aqui são Webhooks que você cria visualmente.

- **Container:** `kreativ_n8n`
- **URL Base Externa:** `https://n8n.extensionista.site`
- **URL Base Interna (Docker):** `http://kreativ_n8n:5678`
- **Autenticação Interface:** Basic Auth (desabilitada por default, gerenciada por e-mail/senha)
- **Autenticação API dos Webhooks:** Definida no nó Webhook (pode ser Nenhuma, Header Auth ou Basic)

### Endpoints Webhook (Exemplo Kreativ)
| Verbo | Endpoint | Descrição |
|-------|----------|-----------|
| `POST`| `/webhook/kreativ-unified-api` | Recebe payload `{"action": "...", "phone": "..."}` roteando para Frappe ou Chatwoot |

> 📖 **Referência:** Veja `docs/N8N_INTEGRATION.md` para a lista de 14 actions suportadas.

---

## 4. Chatwoot (Atendimento Humano)

Omnichannel de suporte para agentes humanos (transbordo).

- **Container:** `kreativ_chatwoot_app`
- **URL Base Externa:** `https://suporte.extensionista.site`
- **URL Base Interna (Docker):** `http://kreativ_chatwoot_app:3000`
- **Autenticação:** Header `api_access_token: {CHATWOOT_API_KEY}` (Token do usuário/agente) ou Client Token (Application)
- **Docs:** `https://www.chatwoot.com/developers/api/`

### Endpoints Principais
| Verbo | Endpoint | Descrição |
|-------|----------|-----------|
| `POST`| `/api/v1/accounts/{account_id}/contacts` | Cria um novo contato (Aluno) |
| `POST`| `/api/v1/accounts/{account_id}/conversations` | Cria uma nova conversa (ticket) |
| `POST`| `/api/v1/accounts/{account_id}/conversations/{c_id}/messages` | Envia mensagem de texto |
| `PATCH`| `/api/v1/accounts/{account_id}/conversations/{c_id}` | Resolve (encerra) a conversa |

---

## 5. Typebot (Flow Builder)

A API do Typebot serve para disparar execuções via backend (invocar um fluxo).

- **Container:** `kreativ_typebot_builder` / `kreativ_typebot_viewer`
- **URL Base Externa:** `https://bot.extensionista.site` (Viewer)
- **Autenticação:** Header `Authorization: Bearer {TOKEN}` (Token Pessoal do Workspace)
- **Docs:** `https://docs.typebot.io/api-reference`

### Endpoints Principais
| Verbo | Endpoint | Descrição |
|-------|----------|-----------|
| `POST`| `/api/v1/typebots/{bot_id}/startChat` | Inicia uma conversa de backend com o bot |
| `POST`| `/api/v1/sessions/{session_id}/continueChat`| Envia uma resposta do usuário e pega a próxima etapa |

> **Nota:** No Kreativ, a Evolution API chama o Typebot nativamente, não precisamos acionar essa API por fora.

---

## 6. Bancos de Dados (Conexões Diretas)

Eles não possuem "REST API" (são TCP/IP binários), mas as IAs e containers acessam assim via string de conexão:

### PostgreSQL (com RAG / pgvector)
- **Container:** `kreativ_postgres`
- **Porta Secundária (Docker interna):** `5432`
- **Conexão:** `postgresql://${PG_USER}:${PG_PASSWORD}@kreativ_postgres:5432/${PG_DATABASE}`
- **Uso:** Armazena dados do N8N, Chatwoot, Typebot, Evolution e Vetores RAG da Educação.

### MariaDB
- **Container:** `frappe_mariadb`
- **Porta (Docker interna):** `3306`
- **Conexão:** `mysql://root:${MARIADB_ROOT_PASSWORD}@frappe_mariadb:3306/{nome_do_site}`
- **Uso:** Fonte da verdade acadêmica (Frappe LMS apenas).

### Redis
- **Container:** `kreativ_redis`
- **Porta (Docker interna):** `6379`
- **Conexão:** `redis://:${REDIS_PASSWORD}@kreativ_redis:6379/{db_index}`
- **Índices Usados:** `0` (Frappe Cache), `1` (Evolution), `3` (Chatwoot).

---

## 7. MinIO (S3 Object Storage)

Servidor de arquivos compatível com a API S3 da AWS. Usado pelo Typebot para hospedar imagens que aparecem no WhatsApp.

- **Container:** `kreativ_minio`
- **Console Web Externa:** `https://files.extensionista.site`
- **API S3 Externa:** `https://s3.extensionista.site`
- **API S3 Interna:** `http://kreativ_minio:9000`
- **Autenticação S3:** Passando `MINIO_ROOT_USER` (Access Key) e `MINIO_ROOT_PASSWORD` (Secret Key).
- **Biblioteca compatível:** `boto3` (Python) ou AWS SDK (Node.js/N8N S3 Node).
