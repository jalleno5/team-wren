"""Generate music from a text description using facebook/musicgen-large.

Install:
    python -m pip install "transformers>=4.41,<5" accelerate torch scipy sentencepiece

Examples:
    python musicgen_generate.py --prompt "An upbeat funk drum groove with slap bass" --duration 10
    python musicgen_generate.py --prompt "Slow jazz instrumental with brushed drums" --duration 15 --output jazz.wav
    python musicgen_generate.py  # interactively prompts for description
"""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Generate WAV music with Meta MusicGen Large")
    parser.add_argument("--prompt", type=str, default=None, help="Text description of the music")
    parser.add_argument("--duration", type=float, default=10.0, help="Approximate audio seconds (1-30; default: 10)")
    parser.add_argument("--output", type=Path, default=Path("musicgen_output_trap.wav"), help="Destination WAV file")
    parser.add_argument("--model", default="facebook/musicgen-large", help="Hugging Face model identifier")
    parser.add_argument("--temperature", type=float, default=1.0, help="Sampling randomness (default: 1.0)")
    parser.add_argument("--guidance-scale", type=float, default=3.0, help="Prompt adherence (default: 3.0)")
    parser.add_argument("--seed", type=int, default=None, help="Optional reproducible seed")
    args = parser.parse_args()

    if not args.prompt:
        args.prompt = input("Describe the music you want to generate: ").strip()
    if not args.prompt:
        parser.error("A nonempty prompt is required")
    if not 1 <= args.duration <= 30:
        parser.error("--duration must be between 1 and 30 seconds")
    if args.temperature <= 0:
        parser.error("--temperature must be greater than zero")
    if args.guidance_scale < 0:
        parser.error("--guidance-scale must be nonnegative")

    import numpy as np
    import torch
    from scipy.io import wavfile
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    has_cuda = torch.cuda.is_available()
    dtype = torch.float16 if has_cuda else torch.float32
    print(f"Device: {'CUDA (automatic GPU/CPU placement)' if has_cuda else 'CPU'}")
    print(f"Loading {args.model} (first run downloads model weights)...")
    processor = AutoProcessor.from_pretrained(args.model)
    # accelerate dispatches layers to GPU/CPU if the model exceeds available VRAM.
    model = MusicgenForConditionalGeneration.from_pretrained(
        args.model, torch_dtype=dtype, device_map="auto" if has_cuda else "cpu"
    )
    model.eval()

    inputs = processor(text=[args.prompt], padding=True, return_tensors="pt")
    # Place input IDs on the device used by the text encoder (typically cuda:0).
    inputs = {key: value.to(model.device) for key, value in inputs.items()}

    # MusicGen creates roughly 50 audio tokens per second.
    tokens = round(args.duration * 50)
    if args.seed is not None:
        torch.manual_seed(args.seed)
        if has_cuda:
            torch.cuda.manual_seed_all(args.seed)

    print(f"Generating approximately {args.duration:g}s of music: {args.prompt}")
    with torch.inference_mode():
        audio = model.generate(
            **inputs,
            do_sample=True,
            temperature=args.temperature,
            guidance_scale=args.guidance_scale,
            max_new_tokens=tokens,
        )

    # Model outputs [batch, channels, samples].  MusicGen Large is mono at 32 kHz.
    waveform = audio[0, 0].detach().float().cpu().numpy()
    waveform = np.clip(waveform, -1, 1)
    pcm16 = (waveform * 32767).astype(np.int16)
    sample_rate = model.config.audio_encoder.sampling_rate
    args.output.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(args.output), sample_rate, pcm16)
    print(f"Saved: {args.output.resolve()} ({len(waveform) / sample_rate:.2f}s, {sample_rate} Hz)")


if __name__ == "__main__":
    main()
