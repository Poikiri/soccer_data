.PHONY: bootstrap up install run serve down

VENV = .venv/bin

bootstrap: up install run

up:
	[ -f .env ] || cp .env.example .env
	docker compose up -d
	until docker compose exec -T postgres pg_isready -U soccer > /dev/null 2>&1; do sleep 1; done

install:
	python3 -m venv .venv
	$(VENV)/pip install -q -r requirements.txt

run:
	set -a && [ -f .env ] && . ./.env; set +a; $(VENV)/python flows/pipeline.py

serve:
	set -a && [ -f .env ] && . ./.env; set +a; PREFECT_SERVE=1 $(VENV)/python flows/pipeline.py

down:
	docker compose down
