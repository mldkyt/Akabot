FROM python:3.12-alpine
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY features features/.
COPY utils utils/.
COPY database.py .
COPY main.py .
COPY LATEST_3.4.md .
COPY LATEST_3.2.md .
COPY LATEST_3.1.md .
COPY lang/ lang/.
COPY docs/ docs/.
COPY configs/ configs/.

STOPSIGNAL SIGKILL

CMD ["python", "/app/main.py"]
