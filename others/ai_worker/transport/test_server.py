"""Format, deadline, cancellation and idle expiry regressions; real ASR lives in asr_probe."""
import io
import math
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
import wave

from transport.server import Jobs, Rejected, validate_audio


def wav(*, rate=16000, channels=1, width=2, seconds=0.1):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setparams((channels, width, rate, 0, "NONE", "NONE"))
        audio.writeframes(b"\0" * int(rate * seconds) * channels * width)
    return stream.getvalue()


class WorkerTests(unittest.TestCase):
    def test_pcm_format_and_complete_payload(self):
        validate_audio(wav())
        for data in (wav(rate=48000), wav(channels=2), wav(width=1), wav()[:-2], wav() + b"x", b"WebM" * 40,
                     wav(seconds=0.01), wav(seconds=31)):
            with self.subTest(length=len(data)), self.assertRaises(Rejected):
                validate_audio(data)

    def test_deadline_input(self):
        jobs = Jobs()
        for timeout in (math.nan, math.inf, -1, 0, 31):
            with self.assertRaises(Rejected):
                jobs.submit(str(uuid4()), wav(), timeout)
        self.assertIsNone(jobs.active)

    def test_idle_result_expiry(self):
        jobs = Jobs()
        jobs.items["expired"] = {"expires": time.monotonic() - 1}
        jobs.prune()
        self.assertFalse(jobs.items)

    def test_hung_native_child_is_killed_and_reaped(self):
        real_popen = subprocess.Popen
        children = []

        def hung(*_args, **kwargs):
            child = real_popen([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
            children.append(child)
            return child

        for cancel in (True, False):
            jobs = Jobs()
            key = str(uuid4())
            with patch("transport.server.subprocess.Popen", hung):
                jobs.submit(key, wav(), 3 if cancel else 0.05)
                deadline = time.monotonic() + 3
                while not children or jobs.items[key]["process"] is None:
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.01)
                if cancel:
                    jobs.remove(key)
                while jobs.active:
                    self.assertLess(time.monotonic(), deadline)
                    time.sleep(0.01)
                self.assertIsNotNone(children[-1].poll())
                if cancel:
                    self.assertNotIn(key, jobs.items)
                else:
                    self.assertEqual(jobs.get(key)["state"], "timed_out")
                    jobs.remove(key)
                jobs.close()
                self.assertFalse(jobs.items)


if __name__ == "__main__":
    unittest.main()
