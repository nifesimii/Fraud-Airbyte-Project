# Airflow + Airbyte Cloud Data Platform

Modern data orchestration platform with Airflow on K3s, Airbyte Cloud, and multi-database sources.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Kubernetes Cluster (Airflow Namespace)          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📊 Orchestration Layer                                 │
│  ├── Airflow 3.0.2 (Scheduler, Webserver, Triggerer)   │
│  └── PostgreSQL (Metadata) - Managed by Helm           │
│                                                         │
│  🗄️  Data Sources                                       │
│  ├── PostgreSQL Source (fraud_analytics)               │
│  └── MySQL Source (fraud_data)                         │
│                                                         │
│  🖥️  Management UIs                                     │
│  ├── PgAdmin (PostgreSQL management)                   │
│  └── phpMyAdmin (MySQL management)                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
                         │
                         │ API Integration
                         ▼
                ┌─────────────────┐
                │ Airbyte Cloud   │
                │ (300+ Connectors)│
                └─────────────────┘
```

### Core Components

- **Airflow 3.0.2** on Rancher Desktop (K3s) - Workflow orchestration
- **Airbyte Cloud** - Managed data ingestion (300+ connectors)
- **PostgreSQL Source** - Fraud analytics database
- **MySQL Source** - Transaction data database
- **PgAdmin** - PostgreSQL management UI
- **phpMyAdmin** - MySQL management UI
- **Helm + Kubernetes** - Infrastructure as code

---

## 🚀 Quick Start

### Complete Platform Setup

```bash
# One-command setup (installs everything)
make setup

# Or step-by-step:
make airflow-up           # Deploy Airflow
make components-up        # Deploy databases and UIs
make setup-connections    # Configure Airflow connections
```

### Access Services

```bash
# Airflow UI
make airflow-ui
# → http://localhost:8080 (admin/admin)

# PgAdmin (PostgreSQL management)
make pgadmin-ui
# → http://localhost:8888 (admin@admin.com/admin)

# phpMyAdmin (MySQL management)
make phpmyadmin-ui
# → http://localhost:8889 (airflow/airflow123)

# Check platform status
make status-all
make health-check
```

---

## 🔧 Setup Airbyte Cloud

1. **Sign up**: https://cloud.airbyte.com (free tier available)
2. **Get API key**: Settings → Developer → API Keys
3. **Update secret**: Edit `k8s/secrets/airbyte-secrets.yaml` with your API key
4. **Apply secrets**: 
   ```bash
   cd deployments/airflow
   make install-airbyte-secrets
   make add-airbyte-conn
   ```
5. **See detailed guide**: `docs/AIRBYTE_CLOUD.md`

---

## 📁 Project Structure

```
airflow-k3s-platform/
├── Makefile                          # Root orchestrator
├── README.md
│
├── deployments/
│   └── airflow/
│       ├── Makefile                  # Airflow operations
│       ├── values-override.yaml      # Helm values
│       └── cicd/
│           ├── Dockerfile
│           ├── requirements.txt
│           └── dags/                 # Your DAG files
│
├── k8s/                              # Kubernetes manifests
│   ├── mysql-deployment.yaml
│   ├── postgres-source-deployment.yaml
│   ├── pgadmin-deployment.yaml
│   ├── phpmyadmin-deployment.yaml
│   └── secrets/
│       ├── git-secrets.yaml
│       └── airbyte-secrets.yaml
│
├── docs/
│   ├── AIRBYTE_CLOUD.md             # Airbyte integration guide
│   ├── ARCHITECTURE.md              # Architecture details
│   └── DEPLOYMENT.md                # Deployment guide
│
└── configs/
    └── airflow-connections.yaml
```

---

## 🎯 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Kubernetes** | K3s (Rancher Desktop) | Container orchestration |
| **Orchestration** | Apache Airflow 3.0.2 | Workflow management |
| **Ingestion** | Airbyte Cloud | Data integration (300+ sources) |
| **Metadata DB** | PostgreSQL 14 | Airflow metadata storage |
| **Source DBs** | PostgreSQL 16 + MySQL 8.3 | Sample data sources |
| **DB Management** | PgAdmin + phpMyAdmin | Database administration |
| **Deployment** | Helm 3.x | Package management |
| **Automation** | Makefiles | Build & deployment automation |

---

## 📋 Command Reference

### Setup & Deployment

| Command | Description |
|---------|-------------|
| `make setup` | Complete platform setup (Airflow + all components) |
| `make airflow-up` | Deploy Airflow on Kubernetes |
| `make components-up` | Deploy data sources and management UIs |
| `make setup-connections` | Configure Airflow connections |

### UI Access

| Command | Description |
|---------|-------------|
| `make airflow-ui` | Open Airflow UI → http://localhost:8080 |
| `make pgadmin-ui` | Open PgAdmin → http://localhost:8888 |
| `make phpmyadmin-ui` | Open phpMyAdmin → http://localhost:8889 |
| `make show-urls` | Display all service URLs |

### Status & Monitoring

| Command | Description |
|---------|-------------|
| `make status-all` | Show all pod and service status |
| `make health-check` | Run health checks on all components |
| `make logs-scheduler` | View Airflow scheduler logs |
| `make logs-webserver` | View Airflow webserver logs |
| `make logs-mysql` | View MySQL logs |
| `make logs-postgres-source` | View PostgreSQL source logs |
| `make debug` | Show comprehensive debug information |

### DAG Operations

| Command | Description |
|---------|-------------|
| `make list-dags` | List all available DAGs |
| `make trigger DAG=my_dag` | Trigger specific DAG |
| `make pause DAG=my_dag` | Pause a DAG |
| `make unpause DAG=my_dag` | Unpause a DAG |

### Database Management

| Command | Description |
|---------|-------------|
| `make mysql-connect` | Port-forward to MySQL (localhost:3307) |
| `make postgres-connect` | Port-forward to PostgreSQL source (localhost:5433) |
| `make shell-mysql` | Open MySQL shell |
| `make shell-postgres-source` | Open PostgreSQL source shell |
| `make test-mysql` | Test MySQL connection with sample query |
| `make test-postgres-source` | Test PostgreSQL connection with sample query |
| `make test-all` | Run all database tests |

### Connections

| Command | Description |
|---------|-------------|
| `make list-connections` | List all Airflow connections |
| `make add-connection CONN_ID=... CONN_TYPE=... CONN_HOST=...` | Add custom connection |

### Maintenance

| Command | Description |
|---------|-------------|
| `make restart-airflow` | Restart Airflow pods |
| `make restart-components` | Restart database and UI components |
| `make upgrade-airflow` | Upgrade Airflow with new image |
| `make clean-failed-pods` | Remove failed/error pods |

### Teardown

| Command | Description |
|---------|-------------|
| `make uninstall-components` | Remove databases and UIs only |
| `make uninstall-airflow` | Remove Airflow only |
| `make uninstall-all` | Remove everything (requires confirmation) |

### Development

| Command | Description |
|---------|-------------|
| `make dev-setup` | Alias for complete setup |
| `make dev-reset` | Full teardown and redeploy |
| `make quick-restart` | Restart Airflow without rebuild |

---

## 💾 Database Information

### PostgreSQL Source (fraud_analytics)

**Access via PgAdmin**: http://localhost:8888
**Direct connection**: `psql -h 127.0.0.1 -p 5433 -U postgres -d fraud_analytics`
**Password**: `postgres`

**Sample Tables**:
- `customer_profiles` - Customer information with risk scores
- `account_activity` - Login and activity logs
- `transaction_logs` - Transaction records

### MySQL Source (fraud_data)

**Access via phpMyAdmin**: http://localhost:8889
**Direct connection**: `mysql -h 127.0.0.1 -P 3307 -u airflow -p`
**Password**: `airflow123` (user: airflow) or `rootpassword` (user: root)

**Sample Tables**:
- `transactions` - Transaction records with fraud flags

### Airflow Metadata (PostgreSQL)

**Managed by**: Helm chart (not accessible via PgAdmin)
**Shell access**: `make shell-postgres`
**Password**: `postgres`

---

## 🛠️ Requirements

### Software
- **Rancher Desktop** or **Docker Desktop** (8GB+ RAM recommended)
- **kubectl** (Kubernetes CLI)
- **helm** (v3.x)
- **make** (build automation)
- **Airbyte Cloud account** (free tier available)

### System Resources
- **RAM**: 8GB minimum, 16GB recommended
- **CPU**: 4 cores minimum
- **Disk**: 20GB free space

### Verification
```bash
# Check installations
kubectl version --client
helm version
docker --version
make --version
```

---

## 👨‍💻 Local Development

### Adding a New DAG

```bash
# 1. Create DAG file
vim deployments/airflow/cicd/dags/my_new_dag.py

# 2. Rebuild Airflow image
cd deployments/airflow
make build

# 3. Upgrade deployment
make upgrade

# 4. Verify DAG appears
make list-dags
```

### Using Git Sync (Recommended)

Your DAGs are automatically synced from GitHub:
- Repository: https://github.com/nifesimii/Fraud-Airbyte-Project.git
- Branch: `main`
- Path: `airflow/dags`
- Sync interval: 60 seconds

Just push to GitHub and wait 60 seconds for automatic sync!

### Updating Dependencies

```bash
# 1. Edit requirements.txt
vim deployments/airflow/cicd/requirements.txt

# 2. Rebuild and upgrade
cd deployments/airflow
make build
make upgrade
```

---

## 🔍 Monitoring & Debugging

### Quick Health Check

```bash
# Check all components
make health-check

# Expected output:
# Airflow Scheduler: ✓
# Airflow Webserver: ✓
# Airflow PostgreSQL: ✓
# Source MySQL: ✓
# Source PostgreSQL: ✓
# PgAdmin: ✓
# phpMyAdmin: ✓
```

### View Logs

```bash
# Airflow components
make logs-scheduler
make logs-webserver
make logs-triggerer

# Databases
make logs-mysql
make logs-postgres-source

# Management UIs
make logs-pgadmin
make logs-phpmyadmin

# All pods
kubectl logs -n airflow -l tier=airflow --tail=100 -f
```

### Debug Issues

```bash
# Comprehensive debug info
make debug

# Check specific pod
kubectl describe pod -n airflow <pod-name>

# Get pod events
kubectl get events -n airflow --sort-by='.lastTimestamp'

# Check resource usage
kubectl top pods -n airflow
```

### Common Issues

#### Pods Not Starting
```bash
# Check pod status
kubectl get pods -n airflow

# Describe failing pod
kubectl describe pod -n airflow <pod-name>

# Check logs
kubectl logs -n airflow <pod-name>
```

#### Can't Access UI
```bash
# Verify service is running
kubectl get svc -n airflow

# Ensure port-forward is active
make airflow-ui  # Run in dedicated terminal
```

#### Database Connection Errors
```bash
# Test connections
make test-mysql
make test-postgres-source

# Verify Airflow connections
make list-connections

# Re-add connections
make setup-connections
```

---

## 🚀 Production Considerations

### Before Production Deployment

#### Security
- [ ] Change all default passwords
- [ ] Use Kubernetes secrets for sensitive data
- [ ] Enable SSL/TLS for all services
- [ ] Set up RBAC (Role-Based Access Control)
- [ ] Use external secrets manager (Vault, AWS Secrets Manager)
- [ ] Enable pod security policies

#### Persistence
- [ ] Enable persistent volumes for Airflow logs
- [ ] Configure database backups
- [ ] Set up disaster recovery plan
- [ ] Use external PostgreSQL for metadata (not Helm-managed)

#### Scalability
- [ ] Configure CeleryExecutor or KubernetesExecutor
- [ ] Set up autoscaling for worker pods
- [ ] Configure resource limits and requests
- [ ] Set up horizontal pod autoscaling

#### Monitoring
- [ ] Set up Prometheus metrics
- [ ] Configure Grafana dashboards
- [ ] Enable logging aggregation (ELK, Loki)
- [ ] Set up alerting (PagerDuty, Slack)

#### Airflow Configuration
- [ ] Set static webserver secret key
- [ ] Configure email notifications
- [ ] Set up external logging (S3, GCS)
- [ ] Enable audit logs
- [ ] Configure connection pooling

### Production Helm Values

```yaml
# Example production values
executor: "KubernetesExecutor"

postgresql:
  enabled: false  # Use external DB

externalDatabase:
  host: prod-postgres.example.com
  database: airflow
  user: airflow
  passwordSecret: airflow-postgres-secret

logs:
  persistence:
    enabled: true
    size: 100Gi
    storageClassName: fast-ssd

webserver:
  replicas: 2
  resources:
    limits:
      cpu: 2000m
      memory: 4Gi
```

---

## 🧪 Testing

### Unit Tests
```bash
# Test database connections
make test-all

# Test individual databases
make test-mysql
make test-postgres-source
```

### Integration Tests
```bash
# Test DAG integrity
cd deployments/airflow
make shell-scheduler
airflow dags test my_dag 2024-01-01
```

### Load Tests
```bash
# Trigger multiple DAGs
for i in {1..10}; do make trigger DAG=test_dag; done

# Monitor resource usage
kubectl top pods -n airflow
```

---

## 📚 Documentation

- **Airbyte Integration**: `docs/AIRBYTE_CLOUD.md`
- **Architecture Details**: `docs/ARCHITECTURE.md`
- **Deployment Guide**: `docs/DEPLOYMENT.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`
- **Makefile Updates**: `MAKEFILE-UPDATES-SUMMARY.md`

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- Apache Airflow community
- Airbyte team for cloud platform
- Rancher Desktop for K3s distribution
- Helm chart maintainers

---

## 📞 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Documentation**: `docs/` directory
- **Airflow Docs**: https://airflow.apache.org/docs/
- **Airbyte Docs**: https://docs.airbyte.com/

---

## 🗺️ Roadmap

- [ ] Add dbt integration for transformations
- [ ] Implement Great Expectations for data quality
- [ ] Add Prometheus/Grafana monitoring stack
- [ ] Create sample fraud detection DAGs
- [ ] Add CI/CD pipeline with GitHub Actions
- [ ] Implement data lineage tracking
- [ ] Add machine learning pipeline examples
- [ ] Create Terraform modules for cloud deployment

---

**Happy Data Engineering! 🚀**