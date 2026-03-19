import hashlib
import os


def fast_checkpoint_hash(filepath: str) -> str:
    """Compute a fast hash of a checkpoint file.

    Reads the first 64KB + last 64KB of the file, combined with
    the file size as a salt, and returns the SHA-256 hex digest.
    """
    CHUNK = 65536  # 64KB
    file_size = os.path.getsize(filepath)

    hasher = hashlib.sha256()
    hasher.update(str(file_size).encode("utf-8"))

    with open(filepath, "rb") as f:
        head = f.read(CHUNK)
        hasher.update(head)

        if file_size > CHUNK * 2:
            f.seek(-CHUNK, os.SEEK_END)
        tail = f.read(CHUNK)
        hasher.update(tail)

    return hasher.hexdigest()


def checkpoint_display_name(filepath: str) -> str:
    """Return the human-readable filename of a checkpoint."""
    return os.path.basename(filepath)
