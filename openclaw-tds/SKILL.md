---
name: openclaw-tds
description: Especialista Antigravity para operações no projeto Kreativ Education (TDS) via Dokploy. Use para consultar o OpenClaw (Qwen2.5-Coder:7b) sobre como atualizar o Frappe/LMS, configurar pt-BR ou aplicar branding sem operações hardcoded no root.
---

# Openclaw TDS (Antigravity)

## Overview
Esta skill permite ao Gemini CLI operar de forma segura no ambiente TDS, utilizando o **OpenClaw (Qwen2.5-Coder:7b)** para resolver problemas de arquitetura e deployment via **Dokploy**.

## Core Mandate: No Hardcoded Root
Todas as operações de deployment, rebuild ou atualização **devem** ser realizadas via Painel ou API do Dokploy. 
- **NÃO** use `docker compose up` manual.
- **NÃO** use `docker build` no host.
- **USE** o script de consulta ou a API do Dokploy.

## Workflow de Consulta (OpenClaw)

1. **Definir o Problema**: Identifique o que precisa ser atualizado ou configurado (ex: Tradução LMS, Branding TDS).
2. **Consultar o Especialista**: Use o script `scripts/query_openclaw.sh` para obter o passo a passo seguro para o Dokploy.
3. **Executar via Dokploy**: Siga as instruções obtidas, priorizando o uso de Volumes Gerenciados e Redeploys via API.

### Exemplo de Uso
```bash
./scripts/query_openclaw.sh "Como traduzir o app lms para pt-BR de forma persistente?"
```

## Recursos

### references/dokploy-api.md
Documentação dos endpoints da API do Dokploy (v0.28.8) para automação de redeploys e gerenciamento de stacks.

### scripts/query_openclaw.sh
Script Bash para chamar a instância Ollama remota com o contexto TDS injetado.

## Personalização TDS (Branding)
Ao personalizar o Frappe LMS, utilize os dados de `ctx.md` (IPEX/UFT/TDS) para configurar:
- Logotipo: IPEX UFT
- Cores: Azul/Branco UFT
- Nome do Site: Kreativ Education (TDS)
