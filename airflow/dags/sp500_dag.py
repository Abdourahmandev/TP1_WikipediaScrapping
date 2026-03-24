import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.providers.docker.operators.docker import DockerOperator
from docker.types import Mount

# ---------------------------------------------------------------------------
# Configuration
# Set PIPELINE_IMAGE in airflow/.env, e.g.:
#   PIPELINE_IMAGE=ghcr.io/your-github-username/tp1-wikipedia:latest
# ---------------------------------------------------------------------------
PIPELINE_IMAGE = os.environ.get(
    "PIPELINE_IMAGE",
    "ghcr.io/abdourahmandev/tp1_wikipediascrapping:latest",
)

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="sp500_daily_scrape",
    description="Scrape the S&P 500 Wikipedia page daily and refresh the report",
    schedule="0 6 * * *",        # Every day at 06:00 UTC
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["sp500", "wikipedia", "pipeline"],
) as dag:

    pull_image = BashOperator(
        task_id="pull_image",
        bash_command=f"docker pull {PIPELINE_IMAGE}",
    )

    run_pipeline = DockerOperator(
        task_id="run_pipeline",
        image=PIPELINE_IMAGE,
        docker_url="unix://var/run/docker.sock",
        mounts=[
            Mount(
                target="/app/data",
                source="sp500-data",    # named volume on the host Docker daemon
                type="volume",
            )
        ],
        auto_remove="success",
        network_mode="bridge",
    )

    pull_image >> run_pipeline
