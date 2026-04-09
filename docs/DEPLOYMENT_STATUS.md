# TDS — Estado do Deploy (09/04/2026)

## Infraestrutura Live

| Serviço | URL | Status |
|---------|-----|--------|
| Frappe LMS | https://lms.ipexdesenvolvimento.cloud | Operacional |
| AnythingLLM RAG | https://rag.ipexdesenvolvimento.cloud | Operacional |
| N8N | https://n8n.ipexdesenvolvimento.cloud | Operacional |
| Chatwoot | https://chat.ipexdesenvolvimento.cloud | Operacional (unhealthy flag) |
| OpenClaw (Ollama) | https://openclaw.ipexdesenvolvimento.cloud | Operacional |

## Cursos Criados (7/7)

| # | Curso | Slug | Caps | Lições | Tutor | TTS | Imagens |
|---|-------|------|------|--------|-------|-----|---------|
| 1 | Agricultura Sustentável | agricultura-sustent-vel-sistemas-agroflorestais-2 | 4 | 9 | Valentine | Sim | Sim (19) |
| 2 | Audiovisual | audiovisual-e-produ-o-de-conte-do-digital-2 | 4 | 12 | Pedro H. | Parcial | Nao |
| 3 | Financas e Empreendedorismo | finan-as-e-empreendedorismo-2 | 4 | 9 | Gabriela | Nao | Nao |
| 4 | Educacao Financeira Melhor Idade | educa-o-financeira-para-a-melhor-idade | 3 | 7 | Gabriela | Nao | Nao |
| 5 | Associativismo e Cooperativismo | associativismo-e-cooperativismo-4 | 3 | 7 | Sofia | Nao | Nao |
| 6 | IA no meu Bolso | ia-no-meu-bolso-intelig-ncia-artificial-para-o-dia-a-dia-2 | 4 | 9 | Rafael | Nao | Nao |
| 7 | SIM - Inspecao Municipal | sim-servi-o-de-inspe-o-municipal-para-pequenos-produtores-2 | 4 | 8 | Sahaa | Nao | Nao |

**Total: 26 capitulos, 61 licoes**

## AnythingLLM Workspaces (7 RAG)

- tds-agricultura-sustentavel
- tds-audiovisual-e-conteudo
- tds-financas-e-empreendedorismo
- tds-educacao-financeira-terceira-idade
- tds-associativismo-e-cooperativismo
- tds-ia-no-meu-bolso
- tds-sim

## PostgreSQL Bridge Table

Tabela `student_frappe_map` criada em `kreativ_edu`:
- phone_number (PK) -> frappe_email, course_slug, batch_slug, rag_workspace
- Indices em phone_number, frappe_email, course_slug

## N8N Workflow

Workflow "Kreativ TDS - Chatwoot RAG Flow" (ID: XYcnRlPZSlfGXOWb):
- Atualizado para roteamento dinamico por workspace RAG
- Usa campo `ragWorkspace` do "Extrair Dados Chatwoot"
- Fallback para workspace `tds` generico

## Pendencias

- [ ] Gerar TTS para cursos 3-7
- [ ] Extrair imagens DOCX para cursos 2-7
- [ ] Importar alunos piloto via CSV
- [ ] Autenticar Ollama Cloud para Gemma 4
- [ ] Teste end-to-end WhatsApp -> RAG correto
- [ ] Verificar Chatwoot unhealthy flag
