.PHONY: help status-all airflow-up airflow-ui

GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
NC := \033[0m

.DEFAULT_GOAL := help

help: ## Show this help
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║      AIRFLOW + AIRBYTE CLOUD DATA PLATFORM                ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)📚 Docs: docs/AIRBYTE_CLOUD.md$(NC)"

airflow-up: ## Deploy Airflow
	@echo "$(YELLOW)━━━ Deploying Airflow ━━━$(NC)"
	@cd deployments/airflow && make reinstall

status-all: ## Show status
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║                  AIRFLOW STATUS                            ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════╝$(NC)"
	@kubectl get pods -n airflow 2>/dev/null || echo "  $(YELLOW)Airflow not deployed$(NC)"
	@echo ""
	@echo "$(GREEN)☁️  Airbyte: Using Airbyte Cloud$(NC)"
	@echo "  Dashboard: $(CYAN)https://cloud.airbyte.com$(NC)"
	@echo "  Docs: $(CYAN)docs/AIRBYTE_CLOUD.md$(NC)"

airflow-ui: ## Access Airflow UI
	@echo "$(GREEN)🚀 Opening Airflow UI$(NC)"
	@echo "  URL: $(CYAN)http://localhost:8080$(NC)"
	@echo "  Login: $(GREEN)admin / admin$(NC)"
	@echo ""
	@cd deployments/airflow && make port-forward

airflow-logs: ## Airflow scheduler logs
	@cd deployments/airflow && make logs-scheduler

list-dags: ## List all DAGs
	@cd deployments/airflow && make list-dags

trigger: ## Trigger DAG (usage: make trigger DAG=my_dag)
	@cd deployments/airflow && make trigger DAG=$(DAG)

restart-airflow: ## Restart Airflow
	@cd deployments/airflow && make reinstall

uninstall-all: ## Uninstall everything
	@cd deployments/airflow && make uninstall

docs: ## Open documentation
	@open docs/AIRBYTE_CLOUD.md 2>/dev/null || cat docs/AIRBYTE_CLOUD.md
