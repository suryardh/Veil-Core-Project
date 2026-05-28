import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def with_retry(fn, *args, max_retries=2, backoff=1.0, retryable=(Exception,), success_fn=None, **kwargs):
    """Retry wrapper.

    Args:
        success_fn: Optional callable yang menerima return value fn.
                    Jika return False, retry dipicu (untuk soft failure
                    seperti ToolResult.fail tanpa raise Exception).
    """
    for attempt in range(max_retries + 1):
        try:
            result = fn(*args, **kwargs)
            if success_fn is not None and not success_fn(result):
                if attempt < max_retries:
                    time.sleep(backoff * (2 ** attempt))
                    continue
            return result
        except retryable:
            if attempt == max_retries:
                raise
            time.sleep(backoff * (2 ** attempt))


def parallel_map(fns, timeout=15):
    with ThreadPoolExecutor(max_workers=min(len(fns), 4)) as pool:
        futures = [pool.submit(fn) for fn in fns]
        results = []
        for f in as_completed(futures, timeout=timeout):
            results.append(f.result())
        return results
