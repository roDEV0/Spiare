FROM python:3.12

WORKDIR /spiare

COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .. /spiare

CMD ["python", "-u", "-m", "watcher.main"]