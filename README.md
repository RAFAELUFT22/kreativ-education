# Kreativ Education 🎓

> **Plataforma de educação conversacional via WhatsApp**, construída sobre o [Frappe LMS](https://github.com/frappe/lms).

Cursos de empreendedorismo para comunidades periféricas no Brasil, acessíveis pelo canal que os alunos já usam: **WhatsApp**.

---

## ⚡ Quickstart

```bash
# 1. Clone o repositório
git clone https://github.com/RAFAELUFT22/kreativ-education.git
cd kreativ-education

# 2. Configure variáveis de ambiente
cp .env.example .env
nano .env  # Preencha as senhas

# 3. Execute o setup (10-15 min)
chmod +x scripts/*.sh
bash scripts/setup.sh

# 4. Acesse o portal
open https://lms.SEU-DOMINIO.com
```

---

## 📐 Arquitetura

```
WhatsApp → Evolution API → Typebot → N8N → Frappe LMS (REST API) → MariaDB
                                      ↓
                                 Chatwoot (transbordo humano)
```

**Frappe LMS** é a fonte da verdade para: cursos, capítulos, lições, quizzes, matrículas e certificados.

> 📖 Veja [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para detalhes.

---

## 📁 Estrutura

```
kreativ-education/
├── docker/              # Infraestrutura Docker
│   ├── docker-compose.yml           # Frappe LMS (9 serviços)
│   └── docker-compose.whatsapp.yml  # WhatsApp stack (10 serviços)
├── scripts/             # setup.sh, health-check.sh, seed-courses.py
├── docs/                # Documentação técnica completa
│   ├── COURSE_CREATION_API.md   ← API REST para cursos
│   ├── N8N_INTEGRATION.md       ← 14 ações N8N ↔ Frappe
│   ├── WHATSAPP_INTEGRATION.md  ← Evolution + Typebot + Chatwoot
│   ├── CONTAINER_APIS.md        ← Referência de todas as APIs dos containers
│   ├── LOCAL_DEVELOPMENT.md     ← Como rodar no seu PC com Ngrok
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── CAPACITY_PLANNING.md
│   └── TROUBLESHOOTING.md
├── guides/              # Guias para assistentes IA
│   ├── AI_IMPLEMENTATION_GUIDE.md  ← Ponto de entrada para IAs
│   ├── KREATIV_CONTEXT.md
│   └── CODING_CONVENTIONS.md
├── courses/             # Templates JSON de cursos
│   ├── templates/       # Modelos genéricos
│   └── tds/             # Cursos reais TDS
└── n8n-workflows/       # Workflows N8N
```

---

## 🤖 Para Assistentes IA

Se você é uma IA (Gemini, Claude, Cursor) trabalhando neste repo:

1. **Leia primeiro**: [`guides/AI_IMPLEMENTATION_GUIDE.md`](guides/AI_IMPLEMENTATION_GUIDE.md)
2. **Entenda o negócio**: [`guides/KREATIV_CONTEXT.md`](guides/KREATIV_CONTEXT.md)
3. **API de cursos**: [`docs/COURSE_CREATION_API.md`](docs/COURSE_CREATION_API.md)

---

## 🖥️ Requisitos

| Requisito | Mínimo |
|-----------|--------|
| RAM | **8 GB** (4GB para o container backend) |
| CPU | 2 vCPU |
| SSD | 50 GB |
| Docker | 24.0+ com Compose V2 |

> ⚠️ O build do frontend precisa de 4GB — veja [docs/CAPACITY_PLANNING.md](docs/CAPACITY_PLANNING.md).

---

## 📚 Documentação

| Documento | Descrição |
|-----------|-----------|
| [LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) | Como rodar a stack no seu PC local com Tunnels (Ngrok) |
| [CONTAINER_APIS.md](docs/CONTAINER_APIS.md) | Guia unificado de Endpoints, IPs e Auth de todos containers |
| [COURSE_CREATION_API.md](docs/COURSE_CREATION_API.md) | Criar cursos, capítulos, lições e quizzes via API |
| [N8N_INTEGRATION.md](docs/N8N_INTEGRATION.md) | 14 ações N8N ↔ Frappe + transbordo Chatwoot |
| [WHATSAPP_INTEGRATION.md](docs/WHATSAPP_INTEGRATION.md) | Evolution API + Typebot + Chatwoot |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Diagrama e componentes |
| [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Deploy passo a passo |
| [CAPACITY_PLANNING.md](docs/CAPACITY_PLANNING.md) | Requisitos de RAM/CPU |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Problemas comuns |
| [AI_IMPLEMENTATION_GUIDE.md](guides/AI_IMPLEMENTATION_GUIDE.md) | Guia para devs e IAs |

---

## 📖 Referências Externas

- [Frappe LMS (GitHub)](https://github.com/frappe/lms)
- [Frappe REST API](https://frappeframework.com/docs/user/en/api/rest)
- [Frappe LMS Docs](https://frappelms.com)
- [Frappe Framework](https://frappeframework.com)

---

## 📄 Licença

MIT — veja [LICENSE](LICENSE).
