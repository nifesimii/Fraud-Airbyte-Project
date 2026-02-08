.PHONY: help status-all airflow-up airflow-ui components-up

GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
RED := \033[0;31m
NC := \033[0m

.DEFAULT_GOAL := help

help: ## Show this help
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║      AIRFLOW + AIRBYTE CLOUD DATA PLATFORM                ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)🚀 QUICK START:$(NC)"
	@echo "  $(GREEN)make setup$(NC)           - Complete platform setup"
	@echo "  $(GREEN)make status-all$(NC)      - Check all services"
	@echo "  $(GREEN)make airflow-ui$(NC)      - Open Airflow UI"
	@echo ""
	@echo "$(CYAN)📦 COMPONENTS:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)📚 Documentation:$(NC)"
	@echo "  Airbyte Cloud: $(BLUE)docs/AIRBYTE_CLOUD.md$(NC)"
	@echo "  Architecture:  $(BLUE)docs/ARCHITECTURE.md$(NC)"

# ============================================================================
# SETUP & DEPLOYMENT
# ============================================================================

setup: airflow-up components-up setup-connections ## Complete platform setup
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║          ✅ PLATFORM SETUP COMPLETE! ✅                     ║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)Access Points:$(NC)"
	@echo "  Airflow:     $(GREEN)make airflow-ui$(NC)     → http://localhost:8080"
	@echo "  PgAdmin:     $(GREEN)make pgadmin-ui$(NC)     → http://localhost:8888"
	@echo "  phpMyAdmin:  $(GREEN)make phpmyadmin-ui$(NC)  → http://localhost:8889"
	@echo "  Airbyte:     $(GREEN)https://cloud.airbyte.com$(NC)"

airflow-up: ## Deploy Airflow on Kubernetes
	@echo "$(YELLOW)━━━ Deploying Airflow ━━━$(NC)"
	@cd deployments/airflow && $(MAKE) all

components-up: ## Deploy MySQL, PostgreSQL source, PgAdmin & phpMyAdmin
	@echo "$(YELLOW)━━━ Deploying Additional Components ━━━$(NC)"
	@cd deployments/airflow && $(MAKE) install-all-components

setup-connections: ## Setup Airflow connections (Airbyte, MySQL, PostgreSQL)
	@echo "$(YELLOW)━━━ Setting up connections ━━━$(NC)"
	@cd deployments/airflow && $(MAKE) setup-connections

# ============================================================================
# STATUS & MONITORING
# ============================================================================

status-all: ## Show status of all services
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║                  PLATFORM STATUS                           ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(CYAN)📊 Kubernetes Pods:$(NC)"
	@kubectl get pods -n airflow 2>/dev/null || echo "  $(YELLOW)Airflow namespace not found$(NC)"
	@echo ""
	@echo "$(CYAN)🔗 Services:$(NC)"
	@kubectl get svc -n airflow 2>/dev/null || echo "  $(YELLOW)No services found$(NC)"
	@echo ""
	@echo "$(GREEN)☁️  Airbyte Cloud:$(NC)"
	@echo "  Dashboard: $(CYAN)https://cloud.airbyte.com$(NC)"
	@echo "  Status: $(GREEN)External Service$(NC)"

health-check: ## Run health checks
	@echo "$(YELLOW)Running health checks...$(NC)"
	@echo ""
	@echo -n "Airflow Scheduler: "
	@kubectl get pods -n airflow -l component=scheduler -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q Running && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗$(NC)"
	@echo -n "Airflow Webserver: "
	@kubectl get pods -n airflow -l component=webserver -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q Running && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗$(NC)"
	@echo -n "Airflow PostgreSQL: "
	@kubectl get pods -n airflow -l app.kubernetes.io/name=postgresql -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q Running && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗$(NC)"
	@echo -n "Source MySQL: "
	@kubectl get pods -n airflow -l app=mysql -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q Running && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗$(NC)"
	@echo -n "Source PostgreSQL: "
	@kubectl get pods -n airflow -l app=postgres-source -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q Running && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗$(NC)"
	@echo -n "PgAdmin: "
	@kubectl get pods -n airflow -l app=pgadmin -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q Running && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗$(NC)"
	@echo -n "phpMyAdmin: "
	@kubectl get pods -n airflow -l app=phpmyadmin -o jsonpath='{.items[0].status.phase}' 2>/dev/null | grep -q Running && echo "$(GREEN)✓$(NC)" || echo "$(RED)✗$(NC)"

# ============================================================================
# UI ACCESS
# ============================================================================

airflow-ui: ## Open Airflow UI
	@echo "$(GREEN)🚀 Opening Airflow UI$(NC)"
	@echo "  URL: $(CYAN)http://localhost:8080$(NC)"
	@echo "  Login: $(GREEN)admin / admin$(NC)"
	@echo ""
	@cd deployments/airflow && $(MAKE) port-forward

pgadmin-ui: ## Open PgAdmin UI (PostgreSQL source)
	@echo "$(GREEN)🗄️  Opening PgAdmin UI$(NC)"
	@echo "  URL: $(CYAN)http://localhost:8888$(NC)"
	@echo "  Login: $(GREEN)admin@admin.com / admin$(NC)"
	@echo "  Manages: $(YELLOW)PostgreSQL Source (fraud_analytics)$(NC)"
	@echo ""
	@cd deployments/airflow && $(MAKE) port-forward-pgadmin

phpmyadmin-ui: ## Open phpMyAdmin UI (MySQL source)
	@echo "$(GREEN)🗄️  Opening phpMyAdmin UI$(NC)"
	@echo "  URL: $(CYAN)http://localhost:8889$(NC)"
	@echo "  Server: $(GREEN)mysql$(NC)"
	@echo "  Username: $(GREEN)airflow$(NC) or $(GREEN)root$(NC)"
	@echo "  Password: $(GREEN)airflow123$(NC) or $(GREEN)rootpassword$(NC)"
	@echo ""
	@cd deployments/airflow && $(MAKE) port-forward-phpmyadmin

mysql-connect: ## Connect to MySQL (port-forward)
	@echo "$(GREEN)🔌 Connecting to MySQL$(NC)"
	@cd deployments/airflow && $(MAKE) port-forward-mysql

postgres-connect: ## Connect to PostgreSQL source (port-forward)
	@echo "$(GREEN)🔌 Connecting to PostgreSQL Source$(NC)"
	@cd deployments/airflow && $(MAKE) port-forward-postgres-source

# ============================================================================
# LOGS & DEBUG
# ============================================================================

logs-scheduler: ## Airflow scheduler logs
	@cd deployments/airflow && $(MAKE) logs-scheduler

logs-webserver: ## Airflow webserver logs
	@cd deployments/airflow && $(MAKE) logs-webserver

logs-mysql: ## MySQL logs
	@kubectl logs -n airflow -l app=mysql --tail=100 -f

logs-postgres-source: ## PostgreSQL source logs
	@kubectl logs -n airflow -l app=postgres-source --tail=100 -f

logs-pgadmin: ## PgAdmin logs
	@kubectl logs -n airflow -l app=pgadmin --tail=100 -f

logs-phpmyadmin: ## phpMyAdmin logs
	@kubectl logs -n airflow -l app=phpmyadmin --tail=100 -f

debug: ## Show debug information
	@cd deployments/airflow && $(MAKE) debug

# ============================================================================
# DAG OPERATIONS
# ============================================================================

list-dags: ## List all Airflow DAGs
	@cd deployments/airflow && $(MAKE) list-dags

trigger: ## Trigger DAG (usage: make trigger DAG=my_dag)
	@if [ -z "$(DAG)" ]; then \
		echo "$(RED)Usage: make trigger DAG=<dag_id>$(NC)"; \
		$(MAKE) list-dags; \
		exit 1; \
	fi
	@cd deployments/airflow && $(MAKE) trigger DAG=$(DAG)

pause: ## Pause DAG (usage: make pause DAG=my_dag)
	@cd deployments/airflow && $(MAKE) pause DAG=$(DAG)

unpause: ## Unpause DAG (usage: make unpause DAG=my_dag)
	@cd deployments/airflow && $(MAKE) unpause DAG=$(DAG)


# ============================================================================
# FRAUD DETECTION PIPELINE
# ============================================================================

setup-fraud-pipeline: ## Setup fraud detection pipeline
	@echo "$(YELLOW)━━━ Setting up Fraud Detection Pipeline ━━━$(NC)"
	@cd deployments/airflow && $(MAKE) setup-fraud-pipeline

fraud-pipeline-status: ## Show fraud pipeline status
	@cd deployments/airflow && $(MAKE) fraud-pipeline-status

trigger-fraud: ## Trigger fraud detection pipeline
	@echo "$(YELLOW)🚨 Triggering Fraud Detection Pipeline...$(NC)"
	@cd deployments/airflow && $(MAKE) trigger-fraud-pipeline

unpause-fraud: ## Enable fraud detection pipeline
	@cd deployments/airflow && $(MAKE) unpause-fraud-pipeline

pause-fraud: ## Disable fraud detection pipeline
	@cd deployments/airflow && $(MAKE) pause-fraud-pipeline

check-fraud-dag: ## Check if fraud DAG is loaded
	@cd deployments/airflow && $(MAKE) check-fraud-dag

verify-fraud-data: ## Verify fraud data in databases
	@cd deployments/airflow && $(MAKE) verify-fraud-data

reset-fraud-data: ## Reset fraud detection data (WARNING)
	@cd deployments/airflow && $(MAKE) reset-fraud-data

fraud-help: ## Show fraud pipeline quick start
	@cd deployments/airflow && $(MAKE) fraud-pipeline-help



# ============================================================================
# CONNECTIONS
# ============================================================================

list-connections: ## List Airflow connections
	@cd deployments/airflow && $(MAKE) list-connections

add-connection: ## Add custom connection
	@echo "$(CYAN)Available connection types: http, mysql, postgres, s3, snowflake$(NC)"
	@echo "$(YELLOW)Usage: make add-connection CONN_ID=my_conn CONN_TYPE=mysql CONN_HOST=localhost$(NC)"
	@cd deployments/airflow && $(MAKE) add-conn CONN_ID=$(CONN_ID) CONN_TYPE=$(CONN_TYPE) CONN_HOST=$(CONN_HOST)

# ============================================================================
# TESTING
# ============================================================================

test-mysql: ## Test MySQL connection
	@cd deployments/airflow && $(MAKE) test-mysql

test-postgres-source: ## Test PostgreSQL source connection
	@cd deployments/airflow && $(MAKE) test-postgres-source

test-all: test-mysql test-postgres-source health-check ## Run all tests
	@echo "$(GREEN)✓ All tests passed$(NC)"

# ============================================================================
# MAINTENANCE
# ============================================================================

restart-airflow: ## Restart Airflow services
	@echo "$(YELLOW)Restarting Airflow...$(NC)"
	@cd deployments/airflow && $(MAKE) restart

restart-components: ## Restart MySQL, PostgreSQL, PgAdmin, phpMyAdmin
	@echo "$(YELLOW)Restarting components...$(NC)"
	@kubectl delete pod -n airflow -l app=mysql 2>/dev/null || true
	@kubectl delete pod -n airflow -l app=postgres-source 2>/dev/null || true
	@kubectl delete pod -n airflow -l app=pgadmin 2>/dev/null || true
	@kubectl delete pod -n airflow -l app=phpmyadmin 2>/dev/null || true
	@echo "$(GREEN)✓ Components restarting$(NC)"

upgrade-airflow: ## Upgrade Airflow with new code
	@cd deployments/airflow && $(MAKE) upgrade

clean-failed-pods: ## Clean up failed pods
	@cd deployments/airflow && $(MAKE) cleanup-pods

# ============================================================================
# TEARDOWN
# ============================================================================

uninstall-components: ## Uninstall all data sources and UIs
	@echo "$(RED)Uninstalling components...$(NC)"
	@cd deployments/airflow && $(MAKE) uninstall-components

uninstall-airflow: ## Uninstall Airflow only
	@echo "$(RED)Uninstalling Airflow...$(NC)"
	@cd deployments/airflow && $(MAKE) uninstall

uninstall-all: ## Uninstall everything (WARNING: destructive)
	@echo "$(RED)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(RED)║              ⚠️  WARNING: DESTRUCTIVE ACTION ⚠️              ║$(NC)"
	@echo "$(RED)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(YELLOW)This will delete:$(NC)"
	@echo "  - Airflow namespace and all pods"
	@echo "  - All databases (PostgreSQL, MySQL)"
	@echo "  - All configurations and secrets"
	@echo ""
	@read -p "Type 'DELETE' to confirm: " confirm; \
	if [ "$$confirm" = "DELETE" ]; then \
		cd deployments/airflow && $(MAKE) uninstall; \
		echo "$(GREEN)✓ Platform uninstalled$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

# ============================================================================
# SHELL ACCESS
# ============================================================================

shell-scheduler: ## Shell into scheduler pod
	@cd deployments/airflow && $(MAKE) shell-scheduler

shell-webserver: ## Shell into webserver pod
	@cd deployments/airflow && $(MAKE) shell-webserver

shell-mysql: ## Shell into MySQL
	@cd deployments/airflow && $(MAKE) shell-mysql

shell-postgres-source: ## Shell into PostgreSQL source
	@cd deployments/airflow && $(MAKE) shell-postgres-source

shell-postgres: ## Shell into Airflow PostgreSQL (metadata)
	@cd deployments/airflow && $(MAKE) shell-postgres

# ============================================================================
# DOCUMENTATION
# ============================================================================

docs: ## Open documentation
	@echo "$(CYAN)📚 Documentation:$(NC)"
	@echo "  Airbyte Cloud: docs/AIRBYTE_CLOUD.md"
	@echo "  Architecture:  docs/ARCHITECTURE.md"
	@echo "  Deployment:    docs/DEPLOYMENT.md"
	@cat docs/AIRBYTE_CLOUD.md 2>/dev/null || echo "$(YELLOW)Documentation not found$(NC)"

show-urls: ## Show all service URLs
	@echo "$(CYAN)🌐 Service URLs:$(NC)"
	@echo ""
	@echo "$(GREEN)Local Services:$(NC)"
	@echo "  Airflow:     http://localhost:8080  (admin/admin)"
	@echo "  PgAdmin:     http://localhost:8888  (admin@admin.com/admin)"
	@echo "  phpMyAdmin:  http://localhost:8889  (airflow/airflow123)"
	@echo "  MySQL:       localhost:3307         (direct connection)"
	@echo "  PostgreSQL:  localhost:5433         (direct connection)"
	@echo ""
	@echo "$(GREEN)Cloud Services:$(NC)"
	@echo "  Airbyte:   https://cloud.airbyte.com"
	@echo ""
	@echo "$(YELLOW)To access local services, run:$(NC)"
	@echo "  Airflow:     make airflow-ui"
	@echo "  PgAdmin:     make pgadmin-ui"
	@echo "  phpMyAdmin:  make phpmyadmin-ui"
	@echo "  MySQL:       make mysql-connect"
	@echo "  PostgreSQL:  make postgres-connect"

# ============================================================================
# DEVELOPMENT
# ============================================================================

dev-setup: setup ## Alias for setup (for development)

dev-reset: uninstall-all setup ## Complete reset and redeploy

quick-restart: restart-airflow ## Quick restart without rebuild
