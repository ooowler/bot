import time
from functools import wraps
from prometheus_client import start_http_server, Counter, Histogram


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

    def start(self, _port: int):
        start_http_server(self._port)

    def record(self, function_name: str, elapsed: float) -> None:
        self.call_latency.labels(function=function_name).observe(elapsed)
        self.call_count.labels(function=function_name).inc()

    def track(self, prefix: str = ""):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.perf_counter()
                try:
                    return await func(*args, **kwargs)
                finally:
                    elapsed = time.perf_counter() - start_time
                    name = f"{prefix}{func.__name__}"
                    self.record(name, elapsed)

            return wrapper

        return decorator


metrics = PrometheusClient()
