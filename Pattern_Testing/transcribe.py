"""YourMT3+ inference adapter. Install mt3-infer in this interpreter's environment."""
import argparse
from pathlib import Path


def transcribe(audio: Path, output: Path):
    from mt3_infer import transcribe as infer
    import numpy as np
    import soundfile as sf

    output.parent.mkdir(parents=True, exist_ok=True)
    waveform, sample_rate = sf.read(audio, dtype="float32", always_2d=True)
    if len(waveform) == 0:
        raise ValueError("Cannot transcribe empty audio")
    if not np.isfinite(waveform).all():
        raise ValueError("Cannot transcribe nonfinite audio")
    mono = waveform.mean(axis=1)
    # Float separation stems can exceed full scale. Scale only the inference
    # copy; preserve the stem on disk for correct levels when remixing.
    peak = float(np.abs(mono).max())
    if peak > 1:
        mono = mono / peak
    midi = infer(mono, sr=sample_rate, model="yourmt3")
    midi.save(str(output))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    transcribe(args.audio, args.output)
