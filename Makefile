.PHONY: up down test simulate build logs k8s train-model

up:
	docker compose up --build -d
	@echo "Platform is running. Dashboard: http://localhost:5173"
	@echo "API Gateway:    http://localhost:8000/docs"
	@echo "Grafana:        http://localhost:3000  (admin/admin)"

down:
	docker compose down -v

build:
	docker compose build

logs:
	docker compose logs -f

test:
	docker compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from test-runner

simulate:
	python simulation/send_transactions.py --count 10000 --url http://localhost:8000

train-model:
	cd services/ml-scorer && python train.py

k8s:
	kubectl apply -f k8s/

k8s-down:
	kubectl delete -f k8s/

monitoring:
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
