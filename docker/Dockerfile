# =============================================================================
# TDS -- Frappe LMS Docker Image com branding customizado
#
# Estrategia de customizacao (CSS-driven, upstream-safe):
#   1. Clona frappe/lms (branch develop) via bench get-app
#   2. Sobrescreve APENAS index.css e tailwind.config.js (nunca quebra Vue)
#   3. Injeta tdsPlugin.js (hero banner) via 2 linhas de sed em main.js
#   4. NENHUM componente Vue eh substituido -- sobrevive a updates upstream
#
# Arquivos customizados:
#   - frontend/tailwind.config.js   (tokens de cor TDS)
#   - frontend/src/index.css         (design system CSS completo)
#   - frontend/src/tdsPlugin.js      (injecao DOM do hero via router hook)
#   - frontend/src/main.js           (2 linhas adicionadas via sed)
# =============================================================================

FROM frappe/erpnext:version-15

USER root

RUN chown -R frappe:frappe \
    /home/frappe/frappe-bench/env \
    /home/frappe/frappe-bench/apps \
    /home/frappe/frappe-bench/sites

USER frappe
WORKDIR /home/frappe/frappe-bench

# Criar common_site_config.json temporario para satisfazer o build do frontend
RUN echo '{"socketio_port": 9000}' > sites/common_site_config.json

# Baixar apps necessarios
RUN bench get-app payments --branch version-15 && \
    bench get-app lms --branch develop

# --- TDS Branding: CSS + Tailwind (safe, never breaks Vue) ---
COPY --chown=frappe:frappe lms-custom/tailwind.config.js \
    /home/frappe/frappe-bench/apps/lms/frontend/tailwind.config.js

COPY --chown=frappe:frappe lms-custom/src/index.css \
    /home/frappe/frappe-bench/apps/lms/frontend/src/index.css

# --- TDS Hero Plugin: vanilla JS injected via router hook ---
COPY --chown=frappe:frappe lms-custom/src/tdsPlugin.js \
    /home/frappe/frappe-bench/apps/lms/frontend/src/tdsPlugin.js

# Patch main.js to register the TDS plugin.
# Strategy: add import at the top, and app.use() right after app creation.
# This uses sed with markers that exist in any standard Vue app main.js.
RUN MAIN_JS="/home/frappe/frappe-bench/apps/lms/frontend/src/main.js" && \
    sed -i '1s|^|import { tdsPlugin } from "./tdsPlugin"\n|' "$MAIN_JS" && \
    sed -i '/[a-zA-Z_]\s*=\s*createApp(/a app.use(tdsPlugin)' "$MAIN_JS" && \
    echo "--- TDS: main.js patched ---" && \
    head -15 "$MAIN_JS"

# Instalar dependencias do frontend (com os arquivos ja customizados)
RUN cd /home/frappe/frappe-bench/apps/lms/frontend && \
    yarn install --frozen-lockfile 2>/dev/null || yarn install

# Registrar apps para instalacao
RUN echo "payments" >> sites/apps.txt && \
    echo "lms"      >> sites/apps.txt

# Remover config temporario
RUN rm sites/common_site_config.json
