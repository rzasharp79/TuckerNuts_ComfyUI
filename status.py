class StatusCollector:
    """Collects status messages during AutoTune optimization for output to the user."""

    def __init__(self, max_trials: int):
        self._lines: list[str] = []
        self.max_trials = max_trials
        self.trials_done = 0

    def log(self, message: str):
        """Log a status message and print it to console."""
        self._lines.append(message)
        print(f"[AutoTune] {message}")

    def trial_complete(self, trial_num: int, params: dict, score: float):
        """Record a completed trial with progress percentage."""
        self.trials_done += 1
        pct = (self.trials_done / self.max_trials) * 100
        self.log(
            f"Trial {trial_num + 1}/{self.max_trials} ({pct:.0f}%) - "
            f"steps={params['steps']}, cfg={params['cfg']:.2f}, "
            f"sampler={params['sampler_name']}, scheduler={params['scheduler']}, "
            f"score={score:.4f}"
        )

    def report(self) -> str:
        """Return the full status report as a single string."""
        return "\n".join(self._lines)
