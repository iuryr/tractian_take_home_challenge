all:
	docker compose up -d
	poetry install
	poetry run python setup.py

clean:
	docker compose down --volumes
	rm -rf ./data/inbound/*.json
	rm -rf ./data/outbound/*.json

run:
	poetry run python src/main.py

test:
	docker compose up -d
	poetry run pytest -v

re: clean all
