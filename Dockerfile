FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY modele/ modele/
COPY utils/ utils/

RUN mkdir -p data/bronze

ENTRYPOINT ["python", "main.py"]
