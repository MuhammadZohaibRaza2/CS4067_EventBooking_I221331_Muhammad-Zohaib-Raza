FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5004
RUN useradd -m appuser
USER appuser

CMD ["python", "app.py"]