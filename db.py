import json
import os
import sqlite3
import time
from typing import Optional

import folder_paths

DB_DIR = os.path.join(folder_paths.base_path, "autotune_sampler")
DB_PATH = os.path.join(DB_DIR, "autotune_cache.db")

_CREATE_OPTIMAL = """
CREATE TABLE IF NOT EXISTS optimal_params (
    checkpoint_hash TEXT PRIMARY KEY,
    checkpoint_name TEXT,
    steps INTEGER NOT NULL,
    cfg REAL NOT NULL,
    sampler_name TEXT NOT NULL,
    scheduler TEXT NOT NULL,
    mean_score REAL NOT NULL,
    native_resolution TEXT,
    optimized_at TEXT NOT NULL,
    trials_run INTEGER NOT NULL,
    prompts_per_trial INTEGER NOT NULL
);
"""

_CREATE_HISTORY = """
CREATE TABLE IF NOT EXISTS trial_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    checkpoint_hash TEXT NOT NULL,
    trial_number INTEGER NOT NULL,
    phase TEXT NOT NULL,
    steps INTEGER NOT NULL,
    cfg REAL NOT NULL,
    sampler_name TEXT NOT NULL,
    scheduler TEXT NOT NULL,
    mean_score REAL NOT NULL,
    individual_scores TEXT,
    resolution TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    FOREIGN KEY (checkpoint_hash) REFERENCES optimal_params(checkpoint_hash)
);
"""

MAX_RETRIES = 3
RETRY_DELAY = 1.0


def _get_connection() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def _retry(func):
    """Decorator that retries on database locked errors."""
    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "locked" in str(e) and attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    raise
    return wrapper


@_retry
def init_db():
    with _get_connection() as conn:
        conn.execute(_CREATE_OPTIMAL)
        conn.execute(_CREATE_HISTORY)


@_retry
def get_cached_params(checkpoint_hash: str) -> Optional[dict]:
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM optimal_params WHERE checkpoint_hash = ?",
            (checkpoint_hash,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)


@_retry
def save_optimal_params(
    checkpoint_hash: str,
    checkpoint_name: str,
    steps: int,
    cfg: float,
    sampler_name: str,
    scheduler: str,
    mean_score: float,
    native_resolution: str,
    trials_run: int,
    prompts_per_trial: int,
):
    from datetime import datetime, timezone

    with _get_connection() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO optimal_params
               (checkpoint_hash, checkpoint_name, steps, cfg, sampler_name,
                scheduler, mean_score, native_resolution, optimized_at,
                trials_run, prompts_per_trial)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                checkpoint_hash,
                checkpoint_name,
                steps,
                cfg,
                sampler_name,
                scheduler,
                mean_score,
                native_resolution,
                datetime.now(timezone.utc).isoformat(),
                trials_run,
                prompts_per_trial,
            ),
        )


@_retry
def save_trial(
    checkpoint_hash: str,
    trial_number: int,
    phase: str,
    steps: int,
    cfg: float,
    sampler_name: str,
    scheduler: str,
    mean_score: float,
    individual_scores: list[float],
    resolution: str,
):
    from datetime import datetime, timezone

    with _get_connection() as conn:
        conn.execute(
            """INSERT INTO trial_history
               (checkpoint_hash, trial_number, phase, steps, cfg,
                sampler_name, scheduler, mean_score, individual_scores,
                resolution, recorded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                checkpoint_hash,
                trial_number,
                phase,
                steps,
                cfg,
                sampler_name,
                scheduler,
                mean_score,
                json.dumps(individual_scores),
                resolution,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
