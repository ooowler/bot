import time
from functools import wraps
from prometheus_client import start_http_server, Counter, Histogram
from prometheus_client import Summary, Counter

# TODO переделать
REQUEST_LATENCY = Summary(
    "backpack_request_duration_seconds",
    "Время выполнения запроса к Backpack API",
    ["instruction", "method"],
)

REQUEST_COUNT = Counter(
    "backpack_request_total",
    "Количество запросов к Backpack API",
    ["instruction", "method"],
)


class PrometheusClient:
    def __init__(self):
        self.call_count = Counter(
            "calls_total",
            "Total number of application calls",
            ["function"],
        )
        self.call_latency = Histogram(
            "call_latency_seconds",
            "Latency of function execution",
            ["function"],
        )
        self.call_status = Counter(
            "calls_status_total",
            "Number of calls partitioned by status",
            ["function", "status"],
        )

    def start(self, _port: int):
        start_http_server(self._port)

    def record(self, function_name: str, elapsed: float) -> None:
        self.call_latency.labels(function=function_name).observe(elapsed)
        self.call_count.labels(function=function_name).inc()

    def track(self, prefix: str = ""):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                fname = f"{prefix}{func.__name__}"
                start_ts = time.perf_counter()
                try:
                    result = await func(*args, **kwargs)
                    self.call_status.labels(function=fname, status="success").inc()
                    return result
                except Exception:
                    self.call_status.labels(function=fname, status="failure").inc()
                    raise
                finally:
                    elapsed = time.perf_counter() - start_ts
                    self.call_count.labels(function=fname).inc()
                    self.call_latency.labels(function=fname).observe(elapsed)

            return wrapper

        return decorator


metrics = PrometheusClient()
