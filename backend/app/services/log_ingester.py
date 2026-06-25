
import asyncio
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from app.db.clickhouse.client import insert_logs
from app.services.log_parser import parse_log_line

logger = Logging.getLogger(__name__)

bATCH_SIZE = 1000
FLUSH_INTERVAL = 1.0
MAX_BUFFER_SIZE = 100_000
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0

DEAD_LETTER_DIR = Path("/tmp/sentryops_dead_letters")


class LogIngester:

    def __init__(self):
        self.queue = ingestion_queue
        self.buffer: list[dict] = []
        self.last_flush_time = time.monotonic()
        self._running = False
        self._flush_lock = asyncio.Lock()

        self.lines_received = 0
        self.lines_inserted = 0
        self.lines_dropped = 0
        self.flush_count = 0
        self.error_count = 0



    async def start(self):
        self._running = True
        logger.info("Log ingester starting.....")

        await asyncio.gather(
            self._consume_loop(),
            self._flush_timer_loop(),
        )

    
    async def stop(self):

        self._running = False
        if self.buffer:
            await self._flush()

        logger.info(
            f"Log ingester stopped."
            f" Total received: {self.lines_received}"
            f" inserted: {self.lines_inserted}"
            f"dropped: {self.lines_dropped}"
        )



    async def _consume_loop(self):

        while self._running:
            try:
                
                entry = await asyncio.wait_for(self.queue.get(), timeout=0.5)

                self.lines_received += 1 

                if len(self.buffer) >= MAX_BUFFER_SIZE:
                    self.buffer.pop(0)
                    self.lines_dropped += 1
                    if self.lines_dropped % 1000 == 0:
                        logger.warning(f"Backpressure: dropped {self.lines_dropped} lines total")


                parsed = parse_log_line(entry)
                self.buffer.append(parsed)

                if len(self.buffer) >= bATCH_SIZE:
                    await self._flush()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in consume loop: {e}")


    async def _flush_timer_loop(self):
        while self._running:
            await asyncio.sleep(FLUSH_INTERVAL)

            elapsed = time.monotonic() - self.last_flush_time
            if elapsed >= FLUSH_INTERVAL and self.buffer:
                await self._flush()


    async def _flush(self):
        async with self._flush_lock:
            if not self.buffer:
                return


            batch = self.buffer[:]
            self.buffer = []
            self.last_flush_time = time.monotonic()

            success = await self._insert_with_retry(batch)

            if success:
                self.lines_inserted += len(batch)
                self.flush_count += 1
            else:
                self.error_count += 1
                await self._write_to_dead_letter(batch)


    async def _insert_with_retry(self, batch: list[dict]) -> bool:

        for attempt in range(MAX_RETRIES):
            try:
                pass

            except Exception as e:
                logger.warning(f"ClickHouse insert failed (attempt {attempt + 1}/{MAX_RETRIES}: {e})")

                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_BACKOFF * (attempt + 1))
        
        logger.error(f" Failed to insert {len(batch)} logs after {MAX_RETRIES} retries")
        return False


    async def _write_dead_letter(self, batch: list[dict]):

        try:
            DEAD_LETTER_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
            filepath = DEAD_LETTER_DIR / f"batch_{timestamp}.jsonl"


            import json

            lines = [json.dumps(entry, default=str) for entry in batch]
            filepath.write_text("/n".join(lines))
            logger.info(f"Wrote {len(batch)} logs to dead letter: {filepath}")


        except Exception as e:
            logger.error(f"Failed to write dead letter: {e}")


    def get_metrics(self) -> dict:

        return {
            "lines_received": self.lines_received,
            "lines_inserted": self.lines_inserted,
            "lines_dropped": self.lines_dropped,
            "buffer_size": len(self.buffer),
            "flush_count": self.flush_count,
            "error_count": self.error_count,
            "queue_size": self.queue.qsize(),
        }



log_ingester: LogIngester | None = None

async def start_log_ingester(ingestion_queue: asyncio.Queue) -> LogIngester:
    global log_ingester
    log_ingester = LogIngester(ingestion_queue)
    asyncio.create_task(log_ingester.start())

    return log_ingester


async def stop_log_ingester():
    global log_ingester

    if log_ingester:
        await log_ingester.stop()
        log_ingester = None