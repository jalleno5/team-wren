"""Split audio into drums and accompaniment using TorchAudio's pretrained HDemucs."""
import argparse
import os
from pathlib import Path

import numpy as np
import soundfile as sf


def overlap_separate(model, waveform, sample_rate, *, segment_seconds=6, overlap_seconds=1):
    """Bound GPU memory and blend overlapping windows without moving timestamps."""
    import torch

    segment = round(segment_seconds * sample_rate)
    overlap = round(overlap_seconds * sample_rate)
    if not 0 < overlap < segment:
        raise ValueError("Overlap must be positive and shorter than a segment")
    length = waveform.shape[-1]
    result = torch.zeros(len(model.sources), waveform.shape[0], length)
    weights = torch.zeros(length)
    device = next(model.parameters()).device
    for start in range(0, length, segment - overlap):
        end = min(start + segment, length)
        chunk = waveform[:, start:end]
        # A full-sized final window also keeps very short inputs valid for STFT.
        padded = torch.nn.functional.pad(chunk, (0, segment - chunk.shape[-1]))
        with torch.inference_mode():
            separated = model(padded.unsqueeze(0).to(device))[0, :, :, :end-start].cpu()
        window = torch.ones(end - start)
        fade = min(overlap, len(window))
        if start:
            window[:fade] *= torch.linspace(0, 1, fade)
        if end < length:
            window[-fade:] *= torch.linspace(1, 0, fade)
        result[:, :, start:end] += separated * window
        weights[start:end] += window
        if end == length:
            break
    return result / weights.clamp_min(1e-8)


def separate_audio(audio, output_dir):
    import torch
    import torchaudio

    os.environ.setdefault("TORCH_HOME", str(Path(__file__).resolve().parent / "outputs/.model_cache/torch"))
    bundle = torchaudio.pipelines.HDEMUCS_HIGH_MUSDB_PLUS
    waveform, rate = sf.read(audio, dtype="float32", always_2d=True)
    if not len(waveform) or not np.isfinite(waveform).all():
        raise ValueError("Input audio must be nonempty and finite")
    if waveform.shape[1] == 1:
        waveform = np.repeat(waveform, 2, axis=1)
    elif waveform.shape[1] != 2:
        raise ValueError("HDemucs input must be mono or stereo")
    signal = torch.from_numpy(waveform.T.copy())
    if rate != bundle.sample_rate:
        signal = torchaudio.functional.resample(signal, rate, bundle.sample_rate)
    reference = signal.mean(0)
    mean, std = reference.mean(), reference.std(unbiased=False)
    if std < 1e-7:
        raise ValueError("Cannot separate silent audio")
    model = bundle.get_model().to("cuda" if torch.cuda.is_available() else "cpu").eval()
    separated = overlap_separate(model, (signal - mean) / std, bundle.sample_rate) * std
    if not torch.isfinite(separated).all():
        raise ValueError("HDemucs produced nonfinite audio")
    index = model.sources.index("drums")
    drums = separated[index]
    # Preserve the original DC offset once, in the accompaniment, not per stem.
    accompaniment = separated[[i for i in range(len(model.sources)) if i != index]].sum(0) + mean
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Float WAV preserves separator levels; no independent stem normalization.
    for name, data in [("drums", drums), ("accompaniment", accompaniment)]:
        sf.write(output_dir / f"{name}.wav", data.numpy().T, bundle.sample_rate, subtype="FLOAT")
    return output_dir / "drums.wav", output_dir / "accompaniment.wav"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    separate_audio(args.audio, args.output_dir)
