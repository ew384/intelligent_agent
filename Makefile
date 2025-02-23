.PHONY: build run test clean

build:
	docker-compose build

run:
	docker-compose up -d

stop:
	docker-compose down

test:
	pytest tests/

clean:
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -r {} +

