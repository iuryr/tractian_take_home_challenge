all:
	docker compose up -d
	poetry install
	poetry run python setup.py

clean:
	docker compose down --volumes
	rm -rf ./data/inbound/*.json
	rm -rf ./data/outbound/*.json
