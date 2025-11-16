FROM python:3.12-slim

WORKDIR /app
COPY client.py .
COPY eureka_client_lib.py .

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "client.py"]

