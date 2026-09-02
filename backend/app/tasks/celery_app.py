try:
    from celery import Celery
    HAS_CELERY = True
except ImportError:
    HAS_CELERY = False

from app.core.config import settings

if HAS_CELERY:
    celery_app = Celery(
        "unimm_worker",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=[
            "app.tasks.ingestion_tasks",
            "app.tasks.matching_tasks",
            "app.tasks.active_learning"
        ]
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600, # 1 hour max per batch
    )
else:
    import concurrent.futures
    _worker_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="unimm_async_worker")

    class CeleryAsyncResultWrapper:
        def __init__(self, future: concurrent.futures.Future):
            self._future = future

        def get(self, timeout=None):
            return self._future.result(timeout=timeout)

        def result(self, timeout=None):
            return self._future.result(timeout=timeout)

        def ready(self):
            return self._future.done()

    class AsyncWorkerFallback:
        def __init__(self):
            self.conf = {}

        def task(self, *args, **kwargs):
            if len(args) == 1 and callable(args[0]) and not kwargs:
                func = args[0]
                def delay(*task_args, **task_kwargs):
                    return CeleryAsyncResultWrapper(_worker_pool.submit(func, *task_args, **task_kwargs))
                func.delay = delay
                return func

            def decorator(func):
                def delay(*task_args, **task_kwargs):
                    # Non-blocking async execution in dedicated background worker thread
                    return CeleryAsyncResultWrapper(_worker_pool.submit(func, *task_args, **task_kwargs))
                func.delay = delay
                return func
            return decorator

    celery_app = AsyncWorkerFallback()
