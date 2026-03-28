# Dokploy API Reference (v0.28.8)

## Overview
Base URL: `http://46.202.150.132:3000/api`
Auth: Admin credentials via Panel.

## Key Endpoints

### Docker Operations
- `GET /docker.getContainers`: List all containers.
- `POST /docker.restartContainer`: Restart a specific container.
- `GET /docker.getContainersByAppNameMatch`: Search containers by app name.

### Compose Operations
- `POST /compose.create`: Create a new stack.
- `GET /compose.one`: Get stack details.
- `POST /compose.update`: Update stack YAML/env.
- `POST /compose.deploy`: Trigger deployment.
- `POST /compose.redeploy`: Force redeploy (pull latest image).

### Settings & Maintenance
- `POST /settings.reloadTraefik`: Force Traefik reload.
- `POST /settings.cleanUnusedImages`: Prune Docker images.
- `GET /settings.readTraefikFile`: Read Traefik dynamic config.

## Usage Rule
**Never** run `docker-compose up` or `docker build` manually in the VPS root. 
Always use `compose.deploy` or `compose.redeploy` via the Dokploy API/Panel to maintain state consistency.
