import numpy as np

def floats_to_bytes(vec: list[float]) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()

def bytes_to_floats(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)
