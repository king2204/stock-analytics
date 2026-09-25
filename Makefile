.PHONY: install demo pipeline dashboard test lint dbt-docs dagster analysis notebook docker clean

install:        ## install runtime + dev dependencies
	pip install -r requirements-dev.txt

demo:           ## offline end-to-end: synthetic data -> warehouse -> dashboard
	SOURCE=sample python -m pipelines.run
	streamlit run app.py

pipeline:       ## incremental load from the configured source + dbt build
	python -m pipelines.run

dashboard:
	streamlit run app.py

test:
	pytest -q

lint:
	ruff check .

dbt-docs:       ## browse model lineage and column docs on :8080
	cd dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir . --port 8080

dagster:        ## Dagster UI with the daily schedule on :3000
	dagster dev -m pipelines.dagster_defs

analysis:       ## answer the business questions in analysis/business_questions.sql
	python -m analysis.run_queries

notebook:       ## re-execute the analysis notebook in place
	jupyter nbconvert --to notebook --execute --inplace notebooks/portfolio_analysis.ipynb

docker:
	docker compose up --build

clean:
	rm -rf data/warehouse data/lake dbt/target dbt/logs
