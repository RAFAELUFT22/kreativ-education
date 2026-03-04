# Contexto de Negócio — Kreativ Education / TDS

## O Projeto

**Kreativ Educação** (anteriormente TDS — Territórios de Desenvolvimento Social e Inclusão Produtiva) é um projeto educacional que oferece cursos de empreendedorismo, boas práticas e organização produtiva para **comunidades carentes no Brasil**, especialmente no Norte do país (Tocantins).

### Público-Alvo

- **Empreendedores informais** de baixa renda
- **Baixa literacia digital** — muitos só usam WhatsApp
- **Acesso primário via celular** — sem notebook
- **Idioma:** Português brasileiro (pt-BR)

### Proposta de Valor

Educação acessível via o canal que o aluno já usa: **WhatsApp**. O aluno recebe resumos, lições, quizzes e certificados sem sair do app que já conhece.

---

## Cursos Existentes (TDS)

| Curso | Capítulos | Lições | Público |
|-------|-----------|--------|---------|
| Gestão Financeira para Empreendimentos | 2 | 5 | Empreendedores |
| Boas Práticas na Manipulação de Alimentos | 2 | 4 | Produtores de alimentos |
| Organização da Produção para o Mercado | 2 | 3 | Produtores/artesãos |

---

## Fluxo do Aluno

```
1. Aluno recebe link WhatsApp
2. Digita "oi" → menu aparece
3. Escolhe "📖 Estudar Módulo"
4. Recebe resumo + link da lição (Frappe LMS)
5. Completa lição → quiz chega via WhatsApp
6. Responde quiz → nota avaliada
7. Ao completar → certificado gerado e enviado
```

---

## Convenções de Domínio

| Subdomínio | Serviço |
|------------|---------|
| `lms.extensionista.site` | Frappe LMS (portal de cursos) |
| `n8n.extensionista.site` | N8N (automação) |
| `bot.extensionista.site` | Typebot (fluxo visual) |
| `suporte.extensionista.site` | Chatwoot (suporte humano) |
| `dash.extensionista.site` | Metabase (analytics) |

---

## Decisões de Arquitetura

| Decisão | Rationale |
|---------|-----------|
| Frappe LMS como backbone | Open-source, REST API completa, Python, sem vendor lock |
| PostgreSQL para pgvector | Embedding RAG para busca semântica em conteúdo |
| N8N para automação | Visual, integra com tudo, self-hosted |
| Evolution API | Melhor conector WhatsApp open-source |
| Typebot | Flow builder visual, fácil para não-devs |
| Docker + Traefik | Deploy simplificado com SSL automático |

---

*Última atualização: 2026-03-04*
