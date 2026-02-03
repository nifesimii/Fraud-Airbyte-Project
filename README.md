# Airflow + Airbyte Cloud Data Platform

Modern data orchestration platform with Airflow on K3s and Airbyte Cloud.

## Architecture

- **Airflow 3.0.2** on Rancher Desktop (K3s) - Workflow orchestration
- **Airbyte Cloud** - Managed data ingestion (300+ connectors)
- **Helm + Kubernetes** - Infrastructure as code

## Quick Start
```bash
# Deploy Airflow
make airflow-up

# Access UI
make airflow-ui
# http://localhost:8080 (admin/admin)

# Check status
make status-all
```

## Setup Airbyte Cloud

1. Sign up: https://cloud.airbyte.com
2. Get API key: Settings → Developer → API Keys
3. Configure in Airflow: Admin → Connections → Add HTTP connection
4. See `docs/AIRBYTE_CLOUD.md` for details

## Project Structure
```
airflow-k3s-platform/
├── Makefile                    # Main commands
├── README.md
├── deployments/
│   └── airflow/               # Airflow deployment
│       ├── Makefile           # Airflow operations
│       ├── values-override.yaml
│       └── cicd/
│           ├── Dockerfile
│           ├── requirements.txt
│           └── dags/          # Your DAG files
├── docs/
│   └── AIRBYTE_CLOUD.md      # Integration guide
└── configs/
    └── airflow-connections.yaml
```

## Technology Stack

- **Kubernetes**: K3s (Rancher Desktop)
- **Orchestration**: Apache Airflow 3.0.2
- **Ingestion**: Airbyte Cloud
- **Deployment**: Helm charts
- **Automation**: Makefiles

## Commands

| Command | Description |
|---------|-------------|
| `make help` | Show all commands |
| `make airflow-up` | Deploy Airflow |
| `make airflow-ui` | Open Airflow UI |
| `make status-all` | Check pod status |
| `make list-dags` | List all DAGs |
| `make trigger DAG=name` | Trigger specific DAG |
| `make restart-airflow` | Restart Airflow |
| `make uninstall-all` | Remove everything |

## Requirements

- Rancher Desktop or Docker Desktop (8GB+ RAM recommended)
- kubectl
- helm
- Airbyte Cloud account (free tier available)

## Local Development
```bash
# Add new DAG
vim deployments/airflow/cicd/dags/my_new_dag.py

# Rebuild Airflow image
cd deployments/airflow
make build

# Upgrade deployment
make upgrade
```

## Monitoring
```bash
# View scheduler logs
make airflow-logs

# Check specific pod
cd deployments/airflow
make logs-scheduler
make logs-webserver
make logs-postgres
```

## Troubleshooting

See `docs/TROUBLESHOOTING.md` or check pod logs:
```bash
kubectl get pods -n airflow
kubectl logs -n airflow <pod-name>
```

## Production Considerations

For production deployments:
- Enable persistent volumes for logs
- Set up static webserver secret key
- Configure external PostgreSQL
- Set up monitoring/alerting
- Use secrets management (e.g., Vault)

## License

MIT
