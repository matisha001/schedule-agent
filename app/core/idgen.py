"""应用层 ID 生成：雪花式（时间戳 + 进程随机 worker + 序列），适配 BIGINT 非自增主键。

- 单进程内唯一；多 worker 时按 PID 取 worker_id 降低碰撞概率。
- 生成值约 41bit 时间戳 + 10bit worker + 12bit 序列，落在有符号 BIGINT 范围内。
"""

import os
import threading
import time

_SNOWFLAKE_EPOCH_MS = 1_700_000_000_000  # 2023-11-15 前后，仅用于压缩位数


class SnowflakeIDGenerator:
    def __init__(self, worker_id: int | None = None):
        self._lock = threading.Lock()
        self._worker = (worker_id if worker_id is not None else (os.getpid() % 1024)) & 0x3FF
        self._sequence = 0
        self._last_ts = -1

    def next_id(self) -> int:
        with self._lock:
            ts = int(time.time() * 1000) - _SNOWFLAKE_EPOCH_MS
            if ts < self._last_ts:
                raise RuntimeError("系统时钟回拨，拒绝生成 ID")
            if ts == self._last_ts:
                self._sequence = (self._sequence + 1) & 0xFFF
                if self._sequence == 0:
                    ts = self._wait_next_ms()
            else:
                self._sequence = 0
            self._last_ts = ts
            return (ts << 22) | (self._worker << 12) | self._sequence

    def _wait_next_ms(self) -> int:
        while True:
            now = int(time.time() * 1000) - _SNOWFLAKE_EPOCH_MS
            if now > self._last_ts:
                return now
            time.sleep(0.0005)


id_generator = SnowflakeIDGenerator()
