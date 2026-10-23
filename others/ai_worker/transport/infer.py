"""One bounded CPU inference process; audio travels through stdin, never a recording file."""
import io
import json
import os
from pathlib import Path
import sys
import wave

import numpy as np
import sherpa_onnx


def main():
    model = Path(os.environ["LABCONNECT_MODEL_ROOT"]) / "paraformer-2023-09-14"
    with wave.open(io.BytesIO(sys.stdin.buffer.read()), "rb") as audio:
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2").astype(np.float32) / 32768
    recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
        paraformer=str(model / "model.int8.onnx"), tokens=str(model / "tokens.txt"),
        num_threads=2, sample_rate=16000, feature_dim=80, decoding_method="greedy_search", provider="cpu")
    stream = recognizer.create_stream()
    stream.accept_waveform(16000, samples)
    recognizer.decode_stream(stream)
    print(json.dumps({"text": stream.result.text}, ensure_ascii=True))


if __name__ == "__main__":
    main()
