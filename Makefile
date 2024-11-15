# Load environment variables from .env
ifneq ($(wildcard .env),)
	include .env
	export $(shell sed 's/=.*//' .env)
endif

up:
	docker-compose -f docker-compose.yml up -d

build:
	docker-compose -f docker-compose.yml up --build -d

down:
	docker-compose -f docker-compose.yml down

rebuild:
	@$(MAKE) down
	@$(MAKE) build

# TODO TEST
#check-local-k8s-connected:
#	if [ "$$(kubectl config current-context)" = "docker-desktop" ]; then \
#		echo "Successfully switched to docker-desktop context."; \
#	else \
#		echo "Failed to switch to docker-desktop context."; \
#		exit 1; \
#	fi
#
#k8s-local-up:
#	@$(MAKE) check-local-k8s-connected
#	kubectl apply -k k8s/local
#	kubectl port-forward service/dota2-cast-assist-service 8080:8082 &
#
#k8s-local-down:
#	kubectl delete -k k8s/local
#	kill -f "kubectl port-forward service/dota2-cast-assist-service 8080:8082" || true
#
k8s-prod-spinup:
	gcloud container clusters get-credentials $(KUBERNETES_CLUSTER) --zone $(KUBERNETES_CLUSTER_ZONE)
	kustomize build k8s/gke | envsubst | kubectl apply -f -

k8s-prod-down:
	kubectl delete -k k8s/gke