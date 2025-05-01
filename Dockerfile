FROM python:3.11

RUN apt-get update && apt-get install -y --no-install-recommends \
    && pip install --upgrade pip

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY ./src ./src
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["python", "src/bot/main.py"]