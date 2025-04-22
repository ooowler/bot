# run_metrics_server.py
import os
import time
from prometheus_client import start_http_server, Counter

# Указываем директорию для multiprocess режима
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", "/app/metrics")

# Запускаем HTTP-сервер на порту 8000
start_http_server(8000)
print("✅ Prometheus metrics server started on :8000")

# Создаём простой счётчик
heartbeat_counter = Counter(
    "metrics_server_heartbeat_total", "Число тиков метрик сервера"
)

# Инкрементируем счётчик каждую секунду
while True:
    heartbeat_counter.inc()
    time.sleep(5)
