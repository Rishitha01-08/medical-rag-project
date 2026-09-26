"""Small process-local timing helper; values are not service benchmarks."""

import time


def elapsed_ms(started):
    return round((time.perf_counter() - started) * 1000, 3)
