.PHONY: help all clean build install wait-postgres migrate create-session patch-deployments wait-components status port-forward

# Configuration
AIRFLOW_VERSION := 3.0.2
HELM_CHART_VERSION := 1.18.0
IMAGE_NAME := my-dags
IMAGE_TAG := $(shell date +%Y%m%d%H%M%S)
POSTGRES_IMAGE := bitnamilegacy/postgresql:14.10.0
NAMESPACE := airflow
POSTGRES_PASSWORD := postgres
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
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'

all: clean build create-k8s-resources install wait-postgres migrate create-session patch-deployments wait-components status ## Complete installation

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

port-forward: ## Port-forward to webserver
	@echo "$(GREEN)Port-forwarding to Airflow Webserver...$(NC)"
	@echo "Access: $(YELLOW)http://localhost:8080$(NC)"
	@echo "Login: $(GREEN)admin / admin$(NC)"
	@kubectl port-forward -n $(NAMESPACE) svc/airflow-api-server 8080:8080

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

add-aws-conn: ## Add AWS connection
	@kubectl exec -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- \
		airflow connections add aws_conn --conn-type aws --conn-extra '{"region_name":"us-east-1"}'
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

uninstall: ## Uninstall
	@echo "$(RED)Uninstalling Airflow...$(NC)"
	@helm uninstall airflow -n $(NAMESPACE) 2>/dev/null || true
	@kubectl delete namespace $(NAMESPACE) --force --grace-period=0 2>/dev/null || true
	@echo "$(GREEN)✓ Uninstalled$(NC)"

reinstall: uninstall all ## Complete reinstall

shell-scheduler: ## Shell into scheduler
	@kubectl exec -it -n $(NAMESPACE) deploy/airflow-scheduler -c scheduler -- /bin/bash

shell-webserver: ## Shell into webserver  
	@kubectl exec -it -n $(NAMESPACE) deploy/airflow-webserver -c webserver -- /bin/bash

shell-postgres: ## PostgreSQL shell
	@kubectl exec -it -n $(NAMESPACE) airflow-postgresql-0 -- \
		env PGPASSWORD=$(POSTGRES_PASSWORD) psql -U postgres -d postgres

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

restart: ## Restart all Airflow pods
	@echo "$(YELLOW)Restarting Airflow pods...$(NC)"
	@kubectl delete pod -n $(NAMESPACE) -l tier=airflow
	@sleep 10
	@$(MAKE) status
