import time
from loguru import logger
from functools import wraps
from prometheus_client import start_http_server, Counter


class PrometheusClient:
    REQUESTS = Counter("myapp_requests_total", "Total number of requests")

    def requests_inc(self):
        self.REQUESTS.inc()

    # TODO push + labels
    def push(self):
        pass

    async def processing_time(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                end = time.perf_counter()

                self.push()
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}")

        return wrapper


prometheus = PrometheusClient()
