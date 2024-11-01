up:
	docker-compose -f docker-compose.yml up -d

build:
	docker-compose -f docker-compose.yml up --build -d

down:
	docker-compose -f docker-compose.yml down

rebuild:
	@$(MAKE) down
	@$(MAKE) build
