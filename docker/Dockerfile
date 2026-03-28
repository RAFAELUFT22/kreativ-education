# =============================================================================
# Kreativ Education — Frappe LMS Docker Image (V3 - Build Fix)
# =============================================================================

FROM frappe/erpnext:version-15

USER root

# Instalar dependências e preparar o ambiente
RUN chown -R frappe:frappe \
    /home/frappe/frappe-bench/env \
    /home/frappe/frappe-bench/apps \
    /home/frappe/frappe-bench/sites

USER frappe
WORKDIR /home/frappe/frappe-bench

# Criar common_site_config.json temporário para satisfazer o build do frontend
RUN echo '{"socketio_port": 9000}' > sites/common_site_config.json

# Baixar apps necessários
RUN bench get-app payments --branch version-15 && \
    bench get-app lms --branch develop

# Pré-instalar dependências do frontend do LMS
RUN cd /home/frappe/frappe-bench/apps/lms/frontend && \
    yarn install --frozen-lockfile 2>/dev/null || yarn install

# Garantir que os apps estejam listados para instalação
RUN echo "payments" >> sites/apps.txt && \
    echo "lms"      >> sites/apps.txt

# Remover o config temporário para não conflitar com volumes em runtime
RUN rm sites/common_site_config.json
