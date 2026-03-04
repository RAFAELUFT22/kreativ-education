# Integração WhatsApp — Evolution API + Typebot

> Como o canal WhatsApp funciona no Kreativ Education e como configurá-lo.

---

## Arquitetura WhatsApp

```
📱 Aluno (WhatsApp)
    ↓
Evolution API v2 (kreativ_evolution:8080)
    ↓ TYPEBOT_ENABLED=true
Typebot v6 — Viewer (kreativ_typebot_viewer:3000)
    ↓ Blocos "Webhook" (W maiúsculo)
N8N — Unified API (kreativ_n8n:5678)
    ↓
Frappe LMS / Chatwoot / PostgreSQL
    ↓ Resposta
Typebot → Evolution API → WhatsApp
```

---

## 1. Evolution API

### Configuração

| Variável | Valor |
|----------|-------|
| Instância | `europs` |
| Integração | Meta Cloud API (`WHATSAPP-BUSINESS`) |
| URL | `https://evolution.extensionista.site` |
| Auth | `AUTHENTICATION_TYPE: apikey` |
| Typebot | `TYPEBOT_ENABLED: true` |
| Chatwoot | `CHATWOOT_ENABLED: true` |

### Docker Compose

```yaml
evolution-api:
  image: kreativ_evolution_custom
  container_name: kreativ_evolution
  environment:
    SERVER_PORT: 8080
    AUTHENTICATION_TYPE: apikey
    AUTHENTICATION_API_KEY: ${EVOLUTION_API_KEY}
    # Banco de dados
    DATABASE_ENABLED: "true"
    DATABASE_PROVIDER: postgresql
    DATABASE_CONNECTION_URI: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@kreativ_postgres:5432/${EVOLUTION_DB}
    DATABASE_SAVE_DATA_NEW_MESSAGE: "true"
    # Redis
    REDIS_ENABLED: "true"
    REDIS_URI: redis://:${REDIS_PASSWORD}@kreativ_redis:6379/1
    # Chatwoot integrado
    CHATWOOT_ENABLED: "true"
    CHATWOOT_MESSAGE_READ: "true"
    CHATWOOT_BOT_CONTACT: "true"
```

### Funcionalidades Cloud API

- ✅ Botões interativos nativos
- ✅ Listas de seleção
- ✅ Mensagens de template
- ✅ Read receipts (tick azul)
- ✅ Mídia (imagens, vídeos, documentos)

---

## 2. Typebot v6

### Componentes

| Serviço | URL | Container |
|---------|-----|-----------|
| Builder (editor) | `https://typebot.extensionista.site` | `kreativ_typebot_builder` |
| Viewer (runtime) | `https://bot.extensionista.site` | `kreativ_typebot_viewer` |

### Bot Ativo

- **Nome:** Kreativ Educacao
- **ID:** `vnp6x9bqwrx54b2pct5dhqlb`
- **Viewer URL:** `https://bot.extensionista.site/kreativ-educacao`

### ⚠️ Regra Crítica de Blocos Webhook

| Bloco | Comportamento | Usar? |
|-------|--------------|-------|
| `"webhook"` (minúsculo) | Aguarda callback do cliente — Evolution API ignora | ❌ **NÃO USAR** |
| `"Webhook"` (W maiúsculo) | Executa HTTP request server-side | ✅ **SEMPRE** |

### Docker Compose

```yaml
typebot-builder:
  image: baptistearno/typebot-builder:latest
  container_name: kreativ_typebot_builder
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@kreativ_postgres:5432/typebot_db
    NEXT_PUBLIC_VIEWER_URL: https://bot.extensionista.site
    # S3 via MinIO
    S3_ACCESS_KEY: ${MINIO_ROOT_USER}
    S3_SECRET_KEY: ${MINIO_ROOT_PASSWORD}
    S3_BUCKET: typebot
    S3_ENDPOINT: s3.extensionista.site
    S3_SSL: "true"

typebot-viewer:
  image: baptistearno/typebot-viewer:latest
  container_name: kreativ_typebot_viewer
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@kreativ_postgres:5432/typebot_db
    NEXT_PUBLIC_VIEWER_URL: https://bot.extensionista.site
```

---

## 3. Chatwoot (Transbordo Humano)

### Configuração

| Variável | Valor |
|----------|-------|
| URL | `https://suporte.extensionista.site` |
| Versão | `v4.11.0` |
| Locale | `pt_BR` |
| AI | Habilitado (`CW_AI_ENABLED: true`, OpenAI) |
| Container | `kreativ_chatwoot_app` + `kreativ_chatwoot_sidekiq` |

### Docker Compose

```yaml
chatwoot-app:
  image: chatwoot/chatwoot:v4.11.0
  container_name: kreativ_chatwoot_app
  command: sh -c "rm -f /app/tmp/pids/server.pid && bundle exec rails s -p 3000 -b 0.0.0.0"
  environment:
    RAILS_ENV: production
    SECRET_KEY_BASE: ${CHATWOOT_SECRET_KEY}
    FRONTEND_URL: https://suporte.extensionista.site
    DEFAULT_LOCALE: pt_BR
    REDIS_URL: redis://:${REDIS_PASSWORD}@kreativ_redis:6379/3
    POSTGRES_HOST: kreativ_postgres
    POSTGRES_DATABASE: chatwoot_db
    POSTGRES_USERNAME: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    CW_AI_ENABLED: "true"
    OPENAI_API_KEY: ${OPENAI_API_KEY}

chatwoot-sidekiq:
  image: chatwoot/chatwoot:v4.11.0
  container_name: kreativ_chatwoot_sidekiq
  command: bundle exec sidekiq -C config/sidekiq.yml
  environment: *chatwoot_env
```

### Fluxo de Transbordo

```
1. Aluno: "quero falar com alguém"
2. Typebot detecta intenção → Webhook → N8N (action: request_human)
3. N8N:
   - Atualiza handoff_control: status='human'
   - Cria conversa no Chatwoot via API
   - Responde: "Aguarde, um atendente vai te ajudar"
4. Evolution API roteia mensagens para Chatwoot (CHATWOOT_ENABLED=true)
5. Atendente responde no Chatwoot → Evolution → WhatsApp
6. Ao encerrar: N8N atualiza handoff_control: status='bot'
```

### API Chatwoot para N8N

```bash
# Criar contato
POST /api/v1/accounts/{id}/contacts
{"name": "João", "phone_number": "+5563993712345", "identifier": "5563993712345"}

# Criar conversa
POST /api/v1/accounts/{id}/conversations
{"source_id": "5563993712345", "inbox_id": 1, "contact_id": 123}

# Enviar mensagem
POST /api/v1/accounts/{id}/conversations/{conv_id}/messages
{"content": "Olá!", "message_type": "outgoing"}

# Resolver conversa
PATCH /api/v1/accounts/{id}/conversations/{conv_id}
{"status": "resolved"}
```

---

## 4. Configuração Completa no `.env`

```bash
# Evolution API
EVOLUTION_API_KEY=chave_evolution_aqui
EVOLUTION_DB=evolution_db

# Typebot
TYPEBOT_NEXTAUTH_SECRET=secret_typebot
TYPEBOT_ENCRYPTION_SECRET=encryption_typebot
TYPEBOT_ADMIN_EMAIL=admin@extensionista.site

# Chatwoot
CHATWOOT_SECRET_KEY=secret_chatwoot
CHATWOOT_API_KEY=token_de_agente_chatwoot

# Redis (compartilhado)
REDIS_PASSWORD=senha_redis

# MinIO (storage Typebot)
MINIO_ROOT_USER=kreativ_minio
MINIO_ROOT_PASSWORD=senha_minio
```

---

## 5. Subdomínios DNS Necessários

| Subdomínio | Serviço | Tipo |
|------------|---------|------|
| `evolution.extensionista.site` | Evolution API | A record → IP VPS |
| `bot.extensionista.site` | Typebot Viewer | A record → IP VPS |
| `typebot.extensionista.site` | Typebot Builder | A record → IP VPS |
| `suporte.extensionista.site` | Chatwoot | A record → IP VPS |
| `n8n.extensionista.site` | N8N | A record → IP VPS |
| `lms.extensionista.site` | Frappe LMS | A record → IP VPS |

---

## 6. Requisitos de RAM Adicionais (Stack Completo)

| Serviço | RAM |
|---------|-----|
| Evolution API | ~300 MB |
| Typebot Builder | ~300 MB |
| Typebot Viewer | ~200 MB |
| Chatwoot App | ~500 MB |
| Chatwoot Sidekiq | ~300 MB |
| N8N | ~500 MB |
| PostgreSQL (shared) | ~512 MB |
| Redis (shared) | ~64 MB |
| MinIO | ~200 MB |
| **Subtotal Stack WhatsApp** | **~2.9 GB** |
| **+ Frappe LMS Stack** | **~5.9 GB** |
| **Total Completo** | **~8.8 GB** |

> ⚠️ **VPS mínima recomendada para stack completo: 4 vCPU, 16GB RAM**

---

*Última atualização: 2026-03-04*
