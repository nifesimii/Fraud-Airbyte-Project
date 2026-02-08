.PHONY: help all clean build install wait-postgres migrate create-session patch-deployments wait-components status port-forward

# Configuration
AIRFLOW_VERSION := 3.0.2
HELM_CHART_VERSION := 1.18.0
IMAGE_NAME := my-dags
IMAGE_TAG := $(shell date +%Y%m%d%H%M%S)
POSTGRES_IMAGE := bitnamilegacy/postgresql:14.10.0
NAMESPACE := airflow
POSTGRES_PASSWORD := postgres
POSTGRES_SOURCE_PASSWORD := postgres
MYSQL_PASSWORD := airflow123
PGADMIN_PASSWORD := admin
VALUES_FILE := values-override.yaml

# Colors
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
RED := \033[0;31m
NC := \033[0m

.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║         AIRFLOW $(AIRFLOW_VERSION) ON K3S (RANCHER)            ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-30s$(NC) %s\n", $$1, $$2}'

all: clean build create-k8s-resources install wait-postgres migrate create-session patch-deployments wait-components install-all-components status ## Complete installation

clean: ## Clean up existing installation
	@echo "$(YELLOW)━━━ STEP 1: Cleanup ━━━$(NC)"
	@helm uninstall airflow -n $(NAMESPACE) 2>/dev/null || true
	@kubectl delete namespace $(NAMESPACE) --force --grace-period=0 2>/dev/null || true
	@sleep 5
	@echo "$(GREEN)✓ Clean environment$(NC)"

build: ## Build Airflow Docker image
	@echo "$(YELLOW)━━━ STEP 2: Build Airflow Image ━━━$(NC)"
	@docker build -t $(IMAGE_NAME):$(IMAGE_TAG) -f ../cicd/Dockerfile .
	@echo $(IMAGE_TAG) > .airflow-image-tag
	@echo "$(GREEN)✓ Built: $(IMAGE_NAME):$(IMAGE_TAG)$(NC)"

pull-postgres: ## Pull PostgreSQL image
	@echo "$(YELLOW)━━━ STEP 3: Pull PostgreSQL Image ━━━$(NC)"
	@docker pull $(POSTGRES_IMAGE)
	@echo "$(GREEN)✓ PostgreSQL image ready$(NC)"

update-values: ## Update ONLY Airflow image tag in values file
	@echo "$(YELLOW)━━━ Updating Airflow Image Tag ━━━$(NC)"
	@sed -i.bak '/images:/,/airflow:/{s/tag: "[^"]*"/tag: "$(IMAGE_TAG)"/;}' $(VALUES_FILE)
	@echo "$(GREEN)✓ Updated Airflow image to: $(IMAGE_TAG)$(NC)"
	@echo "$(CYAN)  PostgreSQL tag unchanged: 14.10.0$(NC)"

setup-helm: ## Setup Helm repositories
	@echo "$(YELLOW)━━━ STEP 4: Setup Helm ━━━$(NC)"
	@helm repo add apache-airflow https://airflow.apache.org 2>/dev/null || true
	@helm repo update > /dev/null 2>&1
	@echo "$(GREEN)✓ Helm ready$(NC)"

create-namespace: ## Create namespace
	@echo "$(YELLOW)━━━ STEP 5: Create Namespace ━━━$(NC)"
	@kubectl create namespace $(NAMESPACE) 2>/dev/null || true
	@echo "$(GREEN)✓ Namespace: $(NAMESPACE)$(NC)"

create-k8s-resources: create-namespace ## Create K8s resources
	@echo "$(YELLOW)━━━ STEP 6: Create K8s Resources ━━━$(NC)"
	@kubectl apply -f ../k8s/secrets/git-secrets.yaml 2>/dev/null || true
	@echo "$(GREEN)✓ Secrets created$(NC)"

install: pull-postgres update-values setup-helm create-k8s-resources ## Install Airflow
	@echo "$(YELLOW)━━━ STEP 7: Install Airflow $(AIRFLOW_VERSION) ━━━$(NC)"
	@helm install airflow apache-airflow/airflow \
		--version $(HELM_CHART_VERSION) \
		--namespace $(NAMESPACE) \
		-f $(VALUES_FILE) \
		--set images.airflow.pullPolicy=IfNotPresent \
		--set postgresql.image.pullPolicy=IfNotPresent \
		--set migrateDatabaseJob.enabled=false \
		--set createUserJob.useHelmHooks=false \
		--set scheduler.waitForMigrations.enabled=false \
		--set webserver.waitForMigrations.enabled=false \
		--set apiServer.waitForMigrations.enabled=false \
		--set triggerer.waitForMigrations.enabled=false \
		--set dagProcessor.waitForMigrations.enabled=false \
		--timeout 5m || echo "$(YELLOW)⚠ Helm timeout (expected)$(NC)"
	@echo "$(GREEN)✓ Helm chart installed$(NC)"

wait-postgres: ## Wait for PostgreSQL
	@echo "$(YELLOW)━━━ STEP 8: Wait for PostgreSQL ━━━$(NC)"
	@kubectl wait --for=condition=ready pod \
		-l app.kubernetes.io/name=postgresql \
		-n $(NAMESPACE) \
		--timeout=300s
	@echo "$(GREEN)✓ PostgreSQL ready$(NC)"

migrate: wait-postgres ## Run database migration
	@echo "$(YELLOW)━━━ STEP 9: Database Migration ━━━$(NC)"
	@kubectl delete pod -n $(NAMESPACE) airflow-migration 2>/dev/null || true
	@kubectl run airflow-migration \
		--namespace=$(NAMESPACE) \
		--image=$(IMAGE_NAME):$(shell cat .airflow-image-tag 2>/dev/null || echo "latest") \
		--image-pull-policy=IfNotPresent \
		--restart=Never \
		--env="AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://postgres:$(POSTGRES_PASSWORD)@airflow-postgresql:5432/postgres" \
		--command -- sh -c "echo y | airflow db reset"
	@echo "  Waiting for migration..."
	@sleep 30
	@if kubectl logs -n $(NAMESPACE) airflow-migration 2>/dev/null | grep -q "Airflow database tables created"; then \
		echo "$(GREEN)✓ Database migration successful$(NC)"; \
	else \
		echo "$(YELLOW)⚠ Check logs:$(NC)"; \
		kubectl logs -n $(NAMESPACE) airflow-migration 2>&1 | tail -10; \
	fi

create-session: ## Create session table
	@echo "$(YELLOW)━━━ STEP 10: Create Session Table ━━━$(NC)"
	@sleep 5
	@kubectl exec -n $(NAMESPACE) airflow-postgresql-0 -- \
		env PGPASSWORD=$(POSTGRES_PASSWORD) psql -U postgres -d postgres -c " \
		CREATE TABLE IF NOT EXISTS session ( \
			id SERIAL PRIMARY KEY, \
			session_id VARCHAR(255) UNIQUE NOT NULL, \
			data BYTEA, \
			expiry TIMESTAMP \
		);" 2>&1 | grep -v "already exists" || true
	@echo "$(GREEN)✓ Session table ready$(NC)"

patch-deployments: ## Patch deployments
	@echo "$(YELLOW)━━━ STEP 11: Patch Deployments ━━━$(NC)"
	@sleep 20
	@kubectl patch deployment airflow-webserver -n $(NAMESPACE) --type=json \
		-p='[{"op": "remove", "path": "/spec/template/spec/initContainers/0"}]' 2>/dev/null || echo "  Webserver: no init container"
	@kubectl patch deployment airflow-api-server -n $(NAMESPACE) --type=json \
		-p='[{"op": "remove", "path": "/spec/template/spec/initContainers/0"}]' 2>/dev/null || echo "  API Server: no init container"
	@echo "$(GREEN)✓ Deployments patched$(NC)"

create-admin: ## Create admin user
	@echo "$(YELLOW)━━━ STEP 12: Create Admin User ━━━$(NC)"
	@sleep 10
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow users create --username admin --firstname Admin --lastname User \
		--role Admin --email admin@example.com --password admin 2>/dev/null || echo "  User already exists"
	@echo "$(GREEN)✓ Admin user ready$(NC)"

wait-components: ## Wait for components
	@echo "$(YELLOW)━━━ STEP 13: Wait for Components ━━━$(NC)"
	@sleep 30
	@for comp in scheduler triggerer dag-processor; do \
		echo -n "  $$comp..."; \
		if kubectl wait --for=condition=ready pod -l component=$$comp -n $(NAMESPACE) --timeout=180s 2>/dev/null; then \
			echo " $(GREEN)✓$(NC)"; \
		else \
			echo " $(YELLOW)⚠$(NC)"; \
		fi \
	done
	@$(MAKE) create-admin

cleanup-pods: ## Cleanup failed pods
	@kubectl delete pod -n $(NAMESPACE) --field-selector=status.phase=Failed 2>/dev/null || true
	@kubectl delete pod -n $(NAMESPACE) --field-selector=status.phase=Error 2>/dev/null || true
	@kubectl delete pod -n $(NAMESPACE) airflow-migration 2>/dev/null || true

status: cleanup-pods ## Show status
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║       ✅ AIRFLOW $(AIRFLOW_VERSION) ON K3S DEPLOYED! ✅          ║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(BLUE)📊 POD STATUS:$(NC)"
	@kubectl get pods -n $(NAMESPACE)
	@echo ""
	@echo "$(CYAN)Access: $(GREEN)make port-forward$(NC)"
	@echo "$(CYAN)URL: $(GREEN)http://localhost:8080$(NC)"
	@echo "$(CYAN)Login: $(GREEN)admin / admin$(NC)"

# ============================================================================
# ADDITIONAL COMPONENTS (MySQL, PostgreSQL Source, PgAdmin, phpMyAdmin)
# ============================================================================

install-mysql: ## Install MySQL source database
	@echo "$(YELLOW)━━━ Installing MySQL ━━━$(NC)"
	@kubectl apply -f ../k8s/mysql-deployment.yaml
	@echo "  Waiting for MySQL to be ready..."
	@sleep 10
	@kubectl wait --for=condition=ready pod -l app=mysql -n $(NAMESPACE) --timeout=300s || \
		(echo "$(RED)MySQL failed to start. Checking logs:$(NC)" && \
		 kubectl logs -n $(NAMESPACE) -l app=mysql --tail=50 && \
		 exit 1)
	@echo "$(GREEN)✓ MySQL installed$(NC)"

install-postgres-source: ## Install PostgreSQL source database
	@echo "$(YELLOW)━━━ Installing Source PostgreSQL ━━━$(NC)"
	@kubectl apply -f ../k8s/postgres-source-deployment.yaml
	@echo "  Waiting for PostgreSQL to be ready..."
	@sleep 10
	@kubectl wait --for=condition=ready pod -l app=postgres-source -n $(NAMESPACE) --timeout=300s || \
		(echo "$(RED)PostgreSQL failed to start. Checking logs:$(NC)" && \
		 kubectl logs -n $(NAMESPACE) -l app=postgres-source --tail=50 && \
		 exit 1)
	@echo "$(GREEN)✓ Source PostgreSQL installed$(NC)"

install-pgadmin: ## Install PgAdmin (for PostgreSQL source)
	@echo "$(YELLOW)━━━ Installing PgAdmin ━━━$(NC)"
	@kubectl apply -f ../k8s/pgadmin-deployment.yaml
	@kubectl wait --for=condition=ready pod -l app=pgadmin -n $(NAMESPACE) --timeout=300s
	@echo "$(GREEN)✓ PgAdmin installed$(NC)"

install-phpmyadmin: ## Install phpMyAdmin (for MySQL)
	@echo "$(YELLOW)━━━ Installing phpMyAdmin ━━━$(NC)"
	@kubectl apply -f ../k8s/phpmyadmin-deployment.yaml
	@kubectl wait --for=condition=ready pod -l app=phpmyadmin -n $(NAMESPACE) --timeout=300s
	@echo "$(GREEN)✓ phpMyAdmin installed$(NC)"

install-airbyte-secrets: ## Install Airbyte secrets
	@echo "$(YELLOW)━━━ Installing Airbyte Secrets ━━━$(NC)"
	@kubectl apply -f ../k8s/secrets/airbyte-secrets.yaml
	@echo "$(GREEN)✓ Airbyte secrets created$(NC)"

install-all-components: install-mysql install-postgres-source install-pgadmin install-phpmyadmin install-airbyte-secrets ## Install all additional components
	@echo "$(GREEN)✓ All components installed$(NC)"

# ============================================================================
# PORT FORWARDING
# ============================================================================

port-forward: ## Port-forward to Airflow webserver
	@echo "$(GREEN)Port-forwarding to Airflow Webserver...$(NC)"
	@echo "Access: $(YELLOW)http://localhost:8080$(NC)"
	@echo "Login: $(GREEN)admin / admin$(NC)"
	@kubectl port-forward -n $(NAMESPACE) svc/airflow-api-server 8080:8080

port-forward-pgadmin: ## Port-forward to PgAdmin
	@echo "$(GREEN)Port-forwarding to PgAdmin...$(NC)"
	@echo "Access: $(YELLOW)http://localhost:8888$(NC)"
	@echo "Login: $(GREEN)admin@admin.com / admin$(NC)"
	@echo "Manages: $(YELLOW)PostgreSQL Source$(NC)"
	@kubectl port-forward -n $(NAMESPACE) svc/pgadmin 8888:80

port-forward-phpmyadmin: ## Port-forward to phpMyAdmin
	@echo "$(GREEN)Port-forwarding to phpMyAdmin...$(NC)"
	@echo "Access: $(YELLOW)http://localhost:8889$(NC)"
	@echo "Server: $(GREEN)mysql$(NC)"
	@echo "Username: $(GREEN)airflow$(NC) or $(GREEN)root$(NC)"
	@echo "Password: $(GREEN)airflow123$(NC) or $(GREEN)rootpassword$(NC)"
	@kubectl port-forward -n $(NAMESPACE) svc/phpmyadmin 8889:80

port-forward-mysql: ## Port-forward to MySQL
	@echo "$(GREEN)Port-forwarding to MySQL...$(NC)"
	@echo "Connect: $(YELLOW)mysql -h 127.0.0.1 -P 3307 -u airflow -p$(NC)"
	@echo "Password: $(GREEN)airflow123$(NC)"
	@kubectl port-forward -n $(NAMESPACE) svc/mysql 3307:3306

port-forward-postgres-source: ## Port-forward to PostgreSQL source
	@echo "$(GREEN)Port-forwarding to Source PostgreSQL...$(NC)"
	@echo "Connect: $(YELLOW)psql -h 127.0.0.1 -p 5433 -U postgres -d fraud_analytics$(NC)"
	@echo "Password: $(GREEN)postgres$(NC)"
	@kubectl port-forward -n $(NAMESPACE) svc/postgres-source 5433:5432

# ============================================================================
# LOGS
# ============================================================================

logs-scheduler: ## Scheduler logs
	@kubectl logs -n $(NAMESPACE) -l component=scheduler -c scheduler --tail=100 -f

logs-webserver: ## Webserver logs
	@kubectl logs -n $(NAMESPACE) -l component=webserver -c webserver --tail=100 -f

logs-api: ## API server logs
	@kubectl logs -n $(NAMESPACE) -l component=api-server -c api-server --tail=100 -f

logs-dag-processor: ## DAG processor logs
	@kubectl logs -n $(NAMESPACE) -l component=dag-processor -c dag-processor --tail=100 -f

logs-triggerer: ## Triggerer logs
	@kubectl logs -n $(NAMESPACE) -l component=triggerer -c triggerer --tail=100 -f

logs-mysql: ## MySQL logs
	@kubectl logs -n $(NAMESPACE) -l app=mysql --tail=100 -f

logs-postgres-source: ## PostgreSQL source logs
	@kubectl logs -n $(NAMESPACE) -l app=postgres-source --tail=100 -f

logs-pgadmin: ## PgAdmin logs
	@kubectl logs -n $(NAMESPACE) -l app=pgadmin --tail=100 -f

logs-phpmyadmin: ## phpMyAdmin logs
	@kubectl logs -n $(NAMESPACE) -l app=phpmyadmin --tail=100 -f

# ============================================================================
# DAG OPERATIONS
# ============================================================================

list-dags: ## List all DAGs
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- airflow dags list

trigger: ## Trigger DAG (usage: make trigger DAG=my_dag)
	@if [ -z "$(DAG)" ]; then \
		echo "$(RED)Usage: make trigger DAG=<dag_id>$(NC)"; \
		exit 1; \
	fi
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow dags trigger $(DAG)
	@echo "$(GREEN)✓ Triggered: $(DAG)$(NC)"

pause: ## Pause DAG (usage: make pause DAG=my_dag)
	@if [ -z "$(DAG)" ]; then \
		echo "$(RED)Usage: make pause DAG=<dag_id>$(NC)"; \
		exit 1; \
	fi
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow dags pause $(DAG)

unpause: ## Unpause DAG (usage: make unpause DAG=my_dag)
	@if [ -z "$(DAG)" ]; then \
		echo "$(RED)Usage: make unpause DAG=<dag_id>$(NC)"; \
		exit 1; \
	fi
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow dags unpause $(DAG)

# ============================================================================
# CONNECTIONS
# ============================================================================

add-airbyte-conn: ## Add Airbyte Cloud connection
	@echo "$(YELLOW)Adding Airbyte connection...$(NC)"
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow connections add airbyte_cloud \
		--conn-type airbyte \
		--conn-host https://api.airbyte.com/v1 \
		--conn-password "$$(kubectl get secret airbyte-secrets -n $(NAMESPACE) -o jsonpath='{.data.AIRBYTE_API_KEY}' | base64 -d)" 2>/dev/null || echo "  Connection already exists"
	@echo "$(GREEN)✓ Airbyte connection added$(NC)"

add-mysql-conn: ## Add MySQL connection
	@echo "$(YELLOW)Adding MySQL connection...$(NC)"
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow connections add mysql_default \
		--conn-type mysql \
		--conn-host mysql.$(NAMESPACE).svc.cluster.local \
		--conn-port 3306 \
		--conn-login airflow \
		--conn-password $(MYSQL_PASSWORD) \
		--conn-schema fraud_data 2>/dev/null || echo "  Connection already exists"
	@echo "$(GREEN)✓ MySQL connection added$(NC)"

add-postgres-source-conn: ## Add PostgreSQL source connection
	@echo "$(YELLOW)Adding Source PostgreSQL connection...$(NC)"
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow connections add postgres_source \
		--conn-type postgres \
		--conn-host postgres-source.$(NAMESPACE).svc.cluster.local \
		--conn-port 5432 \
		--conn-login postgres \
		--conn-password $(POSTGRES_SOURCE_PASSWORD) \
		--conn-schema fraud_analytics 2>/dev/null || echo "  Connection already exists"
	@echo "$(GREEN)✓ Source PostgreSQL connection added$(NC)"

add-aws-conn: ## Add AWS connection
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow connections add aws_conn --conn-type aws --conn-extra '{"region_name":"us-east-1"}' 2>/dev/null || true
	@echo "$(GREEN)✓ AWS connection added$(NC)"

add-conn: ## Add connection (usage: make add-conn CONN_ID=my_conn CONN_TYPE=http CONN_HOST=example.com)
	@if [ -z "$(CONN_ID)" ] || [ -z "$(CONN_TYPE)" ]; then \
		echo "$(RED)Usage: make add-conn CONN_ID=<id> CONN_TYPE=<type> [CONN_HOST=<host>]$(NC)"; \
		exit 1; \
	fi
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow connections add $(CONN_ID) --conn-type $(CONN_TYPE) $(if $(CONN_HOST),--conn-host $(CONN_HOST))
	@echo "$(GREEN)✓ Connection $(CONN_ID) added$(NC)"

list-connections: ## List all connections
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow connections list

setup-connections: add-airbyte-conn add-mysql-conn add-postgres-source-conn ## Setup all connections

# ============================================================================
# TESTING
# ============================================================================

test-mysql: ## Test MySQL connection
	@echo "$(YELLOW)Testing MySQL...$(NC)"
	@kubectl exec -n $(NAMESPACE) deploy/mysql -- \
		mysql -u airflow -p$(MYSQL_PASSWORD) -e "SELECT 'MySQL Connection successful!' as Status, COUNT(*) as transaction_count FROM fraud_data.transactions;"
	@echo "$(GREEN)✓ MySQL is working$(NC)"

test-postgres-source: ## Test PostgreSQL source connection
	@echo "$(YELLOW)Testing PostgreSQL source...$(NC)"
	@kubectl exec -n $(NAMESPACE) deploy/postgres-source -- \
		psql -U postgres -d fraud_analytics -c "SELECT 'PostgreSQL Connection successful!' as Status, COUNT(*) as customer_count FROM customer_profiles;"
	@echo "$(GREEN)✓ PostgreSQL source is working$(NC)"

# ============================================================================
# MAINTENANCE
# ============================================================================

upgrade: ## Upgrade with new image
	@echo "$(YELLOW)━━━ Quick Upgrade ━━━$(NC)"
	@$(MAKE) build
	@$(MAKE) update-values
	@helm upgrade airflow apache-airflow/airflow \
		--version $(HELM_CHART_VERSION) \
		--namespace $(NAMESPACE) \
		-f $(VALUES_FILE) \
		--reuse-values \
		--timeout 5m
	@kubectl rollout restart deployment -n $(NAMESPACE) -l tier=airflow
	@echo "$(GREEN)✓ Upgrade complete$(NC)"

uninstall: ## Uninstall Airflow
	@echo "$(RED)Uninstalling Airflow...$(NC)"
	@helm uninstall airflow -n $(NAMESPACE) 2>/dev/null || true
	@kubectl delete namespace $(NAMESPACE) --force --grace-period=0 2>/dev/null || true
	@echo "$(GREEN)✓ Uninstalled$(NC)"

uninstall-components: ## Uninstall additional components
	@echo "$(RED)Uninstalling components...$(NC)"
	@kubectl delete -f ../k8s/mysql-deployment.yaml 2>/dev/null || true
	@kubectl delete -f ../k8s/postgres-source-deployment.yaml 2>/dev/null || true
	@kubectl delete -f ../k8s/pgadmin-deployment.yaml 2>/dev/null || true
	@kubectl delete -f ../k8s/phpmyadmin-deployment.yaml 2>/dev/null || true
	@kubectl delete -f ../k8s/secrets/airbyte-secrets.yaml 2>/dev/null || true
	@echo "$(GREEN)✓ Components uninstalled$(NC)"

reinstall: uninstall all ## Complete reinstall

restart: ## Restart all Airflow pods
	@echo "$(YELLOW)Restarting Airflow pods...$(NC)"
	@kubectl delete pod -n $(NAMESPACE) -l tier=airflow
	@sleep 10
	@$(MAKE) status

# ============================================================================
# SHELL ACCESS
# ============================================================================

shell-scheduler: ## Shell into scheduler
	@kubectl exec -it -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- /bin/bash

shell-webserver: ## Shell into webserver  
	@kubectl exec -it -n $(NAMESPACE) deploy/airflow-webserver -c webserver -- /bin/bash

shell-postgres: ## PostgreSQL shell (Airflow metadata)
	@kubectl exec -it -n $(NAMESPACE) airflow-postgresql-0 -- \
		env PGPASSWORD=$(POSTGRES_PASSWORD) psql -U postgres -d postgres

shell-postgres-source: ## Shell into PostgreSQL source
	@kubectl exec -it -n $(NAMESPACE) deploy/postgres-source -- psql -U postgres -d fraud_analytics

shell-mysql: ## MySQL shell
	@kubectl exec -it -n $(NAMESPACE) deploy/mysql -- mysql -u airflow -p$(MYSQL_PASSWORD) fraud_data

# ============================================================================
# UTILITIES
# ============================================================================

get-pods: ## Get all pods
	@kubectl get pods -n $(NAMESPACE)

get-services: ## Get all services
	@kubectl get svc -n $(NAMESPACE)

describe: ## Describe pod (usage: make describe POD=<name>)
	@if [ -z "$(POD)" ]; then \
		echo "$(RED)Usage: make describe POD=<pod-name>$(NC)"; \
		exit 1; \
	fi
	@kubectl describe pod -n $(NAMESPACE) $(POD)

debug: ## Show debug info
	@echo "$(YELLOW)Debug Information:$(NC)"
	@echo ""
	@echo "$(BLUE)Pods:$(NC)"
	@kubectl get pods -n $(NAMESPACE)
	@echo ""
	@echo "$(BLUE)Services:$(NC)"
	@kubectl get svc -n $(NAMESPACE)
	@echo ""
	@echo "$(BLUE)ConfigMaps:$(NC)"
	@kubectl get configmap -n $(NAMESPACE)
	@echo ""
	@echo "$(BLUE)Recent Events:$(NC)"
	@kubectl get events -n $(NAMESPACE) --sort-by='.lastTimestamp' | tail -20

reset-db: ## Reset database (WARNING: deletes all data)
	@echo "$(RED)⚠️  Resetting database...$(NC)"
	@kubectl run airflow-db-reset --restart=Never --rm -i \
		--namespace=$(NAMESPACE) \
		--image=$(IMAGE_NAME):$(shell cat .airflow-image-tag 2>/dev/null || echo "latest") \
		--image-pull-policy=IfNotPresent \
		--env="AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://postgres:$(POSTGRES_PASSWORD)@airflow-postgresql:5432/postgres" \
		--command -- sh -c "echo y | airflow db reset"
	@kubectl delete pod -n $(NAMESPACE) -l tier=airflow
	@echo "$(GREEN)Database reset$(NC)"


# Add this section after the CONNECTIONS section and before TESTING section

# ============================================================================
# FRAUD DETECTION PIPELINE
# ============================================================================

setup-fraud-pipeline: ## Setup fraud detection pipeline (Airflow Variables)
	@echo "$(YELLOW)━━━ Setting up Fraud Detection Pipeline ━━━$(NC)"
	@echo "$(CYAN)ℹ️  You need Airbyte connection IDs first!$(NC)"
	@echo "$(CYAN)   Get them from: https://cloud.airbyte.com/connections$(NC)"
	@echo ""
	@read -p "Enter MySQL Connection ID: " mysql_id; \
	read -p "Enter PostgreSQL Connection ID: " postgres_id; \
	kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow variables set airbyte_mysql_connection_id "$$mysql_id"; \
	kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow variables set airbyte_postgres_connection_id "$$postgres_id"
	@echo "$(GREEN)✓ Fraud pipeline variables configured$(NC)"

list-fraud-variables: ## List fraud pipeline Airflow Variables
	@echo "$(YELLOW)Fraud Pipeline Variables:$(NC)"
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow variables list | grep -E "airbyte_mysql_connection_id|airbyte_postgres_connection_id" || \
		echo "$(RED)No fraud pipeline variables found. Run: make setup-fraud-pipeline$(NC)"

set-fraud-variable: ## Set individual fraud variable (usage: make set-fraud-variable VAR=var_name VALUE=var_value)
	@if [ -z "$(VAR)" ] || [ -z "$(VALUE)" ]; then \
		echo "$(RED)Usage: make set-fraud-variable VAR=<variable_name> VALUE=<value>$(NC)"; \
		echo "$(YELLOW)Example: make set-fraud-variable VAR=airbyte_mysql_connection_id VALUE=abc-123$(NC)"; \
		exit 1; \
	fi
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow variables set $(VAR) "$(VALUE)"
	@echo "$(GREEN)✓ Variable $(VAR) set$(NC)"

trigger-fraud-pipeline: ## Trigger fraud detection pipeline DAG
	@echo "$(YELLOW)🚨 Triggering Fraud Detection Pipeline...$(NC)"
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow dags trigger fraud_detection_pipeline
	@echo "$(GREEN)✓ Fraud pipeline triggered$(NC)"
	@echo "$(CYAN)Monitor: make logs-scheduler$(NC)"

unpause-fraud-pipeline: ## Unpause fraud detection pipeline
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow dags unpause fraud_detection_pipeline 2>/dev/null || \
		echo "$(RED)DAG not found. Deploy it first!$(NC)"
	@echo "$(GREEN)✓ Fraud pipeline unpaused$(NC)"

pause-fraud-pipeline: ## Pause fraud detection pipeline
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow dags pause fraud_detection_pipeline
	@echo "$(YELLOW)⏸  Fraud pipeline paused$(NC)"

check-fraud-dag: ## Check if fraud detection DAG is loaded
	@echo "$(YELLOW)Checking fraud detection DAG...$(NC)"
	@if kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow dags list 2>/dev/null | grep -q "fraud_detection_pipeline"; then \
		echo "$(GREEN)✓ Fraud detection DAG is loaded$(NC)"; \
		kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
			airflow dags show fraud_detection_pipeline; \
	else \
		echo "$(RED)✗ Fraud detection DAG not found$(NC)"; \
		echo "$(YELLOW)Deploy it with: git push or make upgrade$(NC)"; \
	fi

fraud-pipeline-status: ## Show fraud pipeline execution status
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║         FRAUD DETECTION PIPELINE STATUS                   ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)📊 DAG Status:$(NC)"
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow dags list | grep fraud_detection_pipeline 2>/dev/null || \
		echo "$(RED)  DAG not loaded$(NC)"
	@echo ""
	@echo "$(CYAN)🔗 Airflow Variables:$(NC)"
	@$(MAKE) list-fraud-variables
	@echo ""
	@echo "$(CYAN)📈 Recent Runs:$(NC)"
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow dags list-runs -d fraud_detection_pipeline --limit 5 2>/dev/null || \
		echo "$(YELLOW)  No runs yet$(NC)"

verify-fraud-data: ## Verify fraud detection data in databases
	@echo "$(YELLOW)Checking fraud detection data...$(NC)"
	@echo ""
	@echo "$(CYAN)PostgreSQL - customer_transactions:$(NC)"
	@kubectl exec -n $(NAMESPACE) deploy/postgres-source -- \
		psql -U postgres -d fraud_analytics -c \
		"SELECT COUNT(*) as total_transactions, MAX(created_at) as last_created FROM customer_transactions;" 2>/dev/null || \
		echo "$(RED)  Table not found or no data$(NC)"
	@echo ""
	@echo "$(CYAN)MySQL - labeled_transactions:$(NC)"
	@kubectl exec -n $(NAMESPACE) deploy/mysql -- \
		mysql -u airflow -p$(MYSQL_PASSWORD) fraud_data -e \
		"SELECT COUNT(*) as total_labels, SUM(is_fraudulent) as fraudulent_count, MAX(labeled_at) as last_labeled FROM labeled_transactions;" 2>/dev/null || \
		echo "$(RED)  Table not found or no data$(NC)"

reset-fraud-data: ## Reset fraud detection data (WARNING: destructive)
	@echo "$(RED)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(RED)║       ⚠️  WARNING: DELETING FRAUD DETECTION DATA ⚠️         ║$(NC)"
	@echo "$(RED)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@read -p "Type 'DELETE' to confirm: " confirm; \
	if [ "$$confirm" = "DELETE" ]; then \
		echo "$(YELLOW)Dropping PostgreSQL tables...$(NC)"; \
		kubectl exec -n $(NAMESPACE) deploy/postgres-source -- \
			psql -U postgres -d fraud_analytics -c "DROP TABLE IF EXISTS customer_transactions CASCADE;" 2>/dev/null; \
		echo "$(YELLOW)Dropping MySQL tables...$(NC)"; \
		kubectl exec -n $(NAMESPACE) deploy/mysql -- \
			mysql -u airflow -p$(MYSQL_PASSWORD) fraud_data -e "DROP TABLE IF EXISTS labeled_transactions;" 2>/dev/null; \
		echo "$(GREEN)✓ Fraud data reset complete$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

fraud-pipeline-help: ## Show fraud pipeline setup guide
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║       FRAUD DETECTION PIPELINE - QUICK START              ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)📋 Setup Steps:$(NC)"
	@echo ""
	@echo "$(YELLOW)1. Create Airbyte Cloud Sources & Connections$(NC)"
	@echo "   - Go to: https://cloud.airbyte.com"
	@echo "   - Create MySQL source (fraud_data)"
	@echo "   - Create PostgreSQL source (fraud_analytics)"
	@echo "   - Create connections to destination"
	@echo "   - Copy both connection IDs"
	@echo ""
	@echo "$(YELLOW)2. Configure Airflow Variables$(NC)"
	@echo "   $(GREEN)make setup-fraud-pipeline$(NC)"
	@echo ""
	@echo "$(YELLOW)3. Deploy the DAG$(NC)"
	@echo "   - Copy fraud_airbyte_pipeline.py to dags/"
	@echo "   - Git push (auto-syncs) OR make upgrade"
	@echo ""
	@echo "$(YELLOW)4. Verify & Run$(NC)"
	@echo "   $(GREEN)make check-fraud-dag$(NC)         # Check DAG loaded"
	@echo "   $(GREEN)make unpause-fraud-pipeline$(NC)  # Enable DAG"
	@echo "   $(GREEN)make trigger-fraud-pipeline$(NC)  # Run manually"
	@echo ""
	@echo "$(CYAN)🔍 Monitoring:$(NC)"
	@echo "   $(GREEN)make fraud-pipeline-status$(NC)   # Overall status"
	@echo "   $(GREEN)make verify-fraud-data$(NC)       # Check data"
	@echo "   $(GREEN)make logs-scheduler$(NC)          # View logs"
	@echo ""
	@echo "$(CYAN)📚 Documentation:$(NC)"
	@echo "   See: FRAUD_PIPELINE_SETUP.md"
