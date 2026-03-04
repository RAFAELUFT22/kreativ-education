# Guia de Desenvolvimento e Teste Local

> Como rodar a stack completa do Kreativ Education (LMS + WhatsApp) na sua própria máquina (Windows, Mac ou Linux) e expô-la para a internet para testar webhooks reais do WhatsApp.

---

## 1. Requisitos da Máquina Local

Para rodar o "teste real" end-to-end com todas as IAs e containers, seu computador precisará de:
- **Docker Desktop** (Windows/Mac) ou **Docker Engine** (Linux).
- Pelo menos **8GB a 10GB de livre** alocados para o Docker nas configurações.
- **Node.js** e `npm` (recomenda-se v20+).

---

## 2. Lidando com Domínios e HTTPS Localmente

A arquitetura oficial usa o Traefik para gerar certificados SSL (HTTPS). 
**Problema:** O WhatsApp (Evolution API / Meta Cloud) e o N8N **exigem HTTPS válido** para funcionar e enviar webhooks na internet. "localhost" não vai servir.

**A Solução: Tunnels (Ngrok ou Cloudflare)**
Vamos criar túneis seguros conectando o seu PC à internet pública grátis.

### Passo 2A: Criar o arquivo de "Override" do Docker
No diretório `kreativ-education/docker/`, crie um arquivo chamado **`docker-compose.override.yml`**. 
Isso vai expor as portas brutas dos containers para o seu `localhost`, driblando o roteador (Traefik) temporariamente:

```yaml
# docker-compose.override.yml
services:
  frappe-frontend:
    ports:
      - "8080:8080" # Frappe LMS local
  evolution-api:
    ports:
      - "8081:8080" # Evolution local
  n8n:
    ports:
      - "5678:5678" # N8N local
  chatwoot-app:
    ports:
      - "3000:3000" # Chatwoot local
```

### Passo 2B: Instalar e rodar o Tunnel (exemplo com `ngrok` grátis)
Baixe e instale o Ngrok no seu PC, logue na conta gratuita, e exponha as 3 portas que precisam estar na internet:

```bash
# Terminal 1 - Expor Evolution API (Receber mensagens do WhatsApp)
ngrok http 8081

# Terminal 2 - Expor N8N (Receber Webhooks do Typebot/WhatsApp)
ngrok http 5678

# Terminal 3 - Expor Chatwoot (Transbordo)
ngrok http 3000
```
*(O ngrok grátis permite até 3 túneis simultâneos em algumas contas, ou mude para o **Cloudflare Tunnels** (`cloudflared`) se precisar de domínios fixos grátis).*

O Ngrok vai te devolver URLs com HTTPS válido. Exemplo: `https://abcd-12-34.ngrok-free.app`.

---

## 3. Configurando o `.env` Local

Edite o seu arquivo `.env` para apontar para essas novas URLs do Ngrok em vez dos domínios antigos:

```env
# URL do Frappe fica localhost (você acessa pelo navegador normal)
FRAPPE_LMS_URL=http://localhost:8080

# N8N usando o domínio público do ngrok (necessário para o Typebot achar)
WEBHOOK_URL=https://<seu-ngrok-da-porta-5678>.ngrok-free.app

# Chatwoot e Evolution
FRONTEND_URL=https://<seu-ngrok-da-porta-3000>.ngrok-free.app
```

---

## 4. Subindo o Ambiente no seu PC

Agora basta ligar os motores na mesma pasta onde configurou:

```bash
# 1. Crie a rede se ela não existir
docker network create coolify || true
docker network create kreativ_education_net || true

# 2. Suba a base + o LMS
docker compose -f docker/docker-compose.yml up -d

# 3. Suba o stack do WhatsApp
docker compose -f docker/docker-compose.whatsapp.yml up -d
```

### Verificando:
- Abra no PC: `http://localhost:8080` → Deve abrir o Frappe LMS.
- Abra no PC: `http://localhost:5678` → Deve abrir o N8N.
- Teste conectar o WhatsApp mandando request de QRCode ou Cloud API para a URL segura do seu Ngrok: `https://<url-do-ngrok>.app/instance/connectionState/europs`

### Aviso de Limitação do Setup Local do Frappe
Lembre-se do problema de Out-of-Memory (OOM) do Vite do Frappe LMS! 
Mesmo no seu PC local, se o container do `backend` (`kreativ_frappe_backend`) não puder alocar 4GB de RAM pelo Docker Desktop durante o processo `bench build`, a instalação falhará. Certifique-se nas configurações do Docker Desktop que "Resource usage" está configurado pelo menos com 10GB de RAM geral.
