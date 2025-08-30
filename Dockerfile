FROM python:3.12-slim

WORKDIR /app
COPY client.py .
COPY eureka_client_lib.py .
COPY services.json .

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080
EXPOSE 8443

CMD ["python", "client.py"]

