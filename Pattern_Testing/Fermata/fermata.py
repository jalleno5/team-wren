"""Fermata-0.2B wrapper: generation plus best-effort REMI-to-MIDI conversion.

IMPORTANT: The model author does not publish the full codec in the model repository.
MIDI decoding here supports common explicit REMI event spellings and will raise
instead of saving an empty MIDI if the downloaded vocabulary differs.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Optional

import mido

MODEL_ID = "haster/Fermata-0.2B-v1"
GENRES = {"classical", "popular", "jazz", "folk", "electronic", "soundtrack", "world", "religious", "unknown"}
ENSEMBLES = {"solo", "duo", "band", "chamber", "orchestral", "choir", "other"}
MODES = {"major", "minor", "dorian", "phrygian", "lydian", "mixolydian", "none"}


def _read_vocabulary(path: Path) -> dict[str, int]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, list) and all(isinstance(x, str) for x in obj):
        return {token: i for i, token in enumerate(obj)}
    if isinstance(obj, dict):
        for key in ("token_to_id", "stoi", "vocab", "token2id"):
            if key in obj and isinstance(obj[key], dict):
                obj = obj[key]
                break
        if all(isinstance(k, str) and isinstance(v, int) for k, v in obj.items()):
            return obj
        for key in ("id_to_token", "itos", "tokens", "id2token"):
            vals = obj.get(key)
            if isinstance(vals, list):
                return {token: i for i, token in enumerate(vals)}
            if isinstance(vals, dict):
                return {v: int(k) for k, v in vals.items()}
    raise ValueError(f"Unrecognized vocabulary layout: {path}")


def make_header(genre="electronic", ensemble="band", bpm=120, key=0,
                mode="minor", meter="4/4", instruments=(0, 33), drums=True):
    """Key is number of sharps (+) or flats (-), NOT a MIDI root pitch."""
    if genre not in GENRES or ensemble not in ENSEMBLES or mode not in MODES:
        raise ValueError("Invalid genre, ensemble, or mode; refer to model documentation")
    if not 5 <= bpm <= 999 or not -7 <= key <= 7:
        raise ValueError("BPM must be 5..999, key signature -7..7")
    if not re.fullmatch(r"\d+/\d+", meter):
        raise ValueError("meter should look like 4/4 or 6/8")
    programs = list(instruments)
    if not programs and not drums:
        raise ValueError("At least one instrument or a drum track is required")
    if any(not isinstance(x, int) or not 0 <= x <= 127 for x in programs):
        raise ValueError("GM programs must be integers 0..127")
    plan = [f"<TRACK_{i}>" for i in programs]
    if drums:
        plan.append("<DRUM_TRACK>")
    return ["<BOS>", f"<GENRE_{genre}>", f"<ENSEMBLE_{ensemble}>",
            f"<TEMPO_{bpm}>", f"<KEY_{key}:{mode}>", f"<METER_{meter}>",
            "<PLAN>", *plan, "<PLAN_END>"]


def _event(token: str):
    """Extract one REMI event type and its integer payload (if present)."""
    t = token.strip().strip("<>")
    m = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*?)[_:](-?\d+)", t)
    if m:
        return m.group(1).upper(), int(m.group(2))
    return t.upper(), None


def token_diagnostics(tokens: list[str]) -> str:
    """Useful on unfamiliar checkpoints; never claims a failed decode succeeded."""
    from collections import Counter
    events = Counter(_event(t)[0] for t in tokens)
    count = ", ".join(f"{k}: {v}" for k, v in events.most_common(25))
    sample = " ".join(tokens[:110])
    return f"Event families: {count}\nFirst 110 tokens: {sample}"


def tokens_to_midi(tokens: list[str], output: str, *, bpm: int, instruments: list[int],
                   drums: bool, meter: str = "4/4", drum_pitch_correction: bool = False) -> int:
    """Decode Fermata's bar-major REMI+ events, including partial last bars.

    Each beat contains 24 symbolic time units. A note is encoded as:
      <BEAT_b> <SUBPOS_s> <PITCH_p|DRUM_NOTE_p> <DURATION_d> <VELOCITY_v>
    <TRK_i> identifies the zero-based index in the header's instrument plan.
    """
    tpq = 480
    units_per_beat = 24
    numerator, denominator = map(int, meter.split("/"))
    bar_units = round(units_per_beat * numerator * 4 / denominator)
    planned = list(instruments) + ([0] if drums else [])
    bar = -1
    beat = 0
    subpos = 0
    trk = None
    pitch = None
    duration = None
    note_is_drum = False
    in_body = False
    collected: dict[int, list[tuple[int, int, int, int]]] = {}
    note_count = 0

    for raw_token in tokens:
        name, value = _event(raw_token)
        if name == "PLAN_END":
            in_body = True
            continue
        if not in_body:
            continue
        if name == "BAR":
            bar += 1
            beat = 0
            subpos = 0
            trk = None
            pitch = duration = None
        elif name == "TRK" and value is not None:
            trk = value  # Unlike <TRACK_33>, <TRK_1> means plan track #1.
            beat = subpos = 0
            pitch = duration = None
        elif name == "BEAT" and value is not None:
            beat = value
            subpos = 0
        elif name == "SUBPOS" and value is not None:
            subpos = value
        elif name in {"PITCH", "DRUM_NOTE"} and value is not None:
            pitch = value
            note_is_drum = name == "DRUM_NOTE"
            duration = None
        elif name == "DURATION" and value is not None:
            duration = value
        elif name == "VELOCITY" and value is not None:
            if (bar >= 0 and trk is not None and 0 <= trk < len(planned)
                    and pitch is not None and duration is not None and duration > 0):
                if note_is_drum != (drums and trk == len(instruments)):
                    raise ValueError(f"Drum/melodic note mismatch on track {trk}")
                note = pitch - int(drum_pitch_correction and note_is_drum)
                if 0 <= note <= 127:
                    start_units = bar * bar_units + beat * units_per_beat + subpos
                    start = round(start_units * tpq / units_per_beat)
                    end = start + max(1, round(duration * tpq / units_per_beat))
                    # Fermata's velocity is a coarse bucket (0..15), not MIDI 0..127.
                    vel = max(1, min(127, round((value + 0.5) * 8))) if value <= 15 else max(1, min(127, value))
                    collected.setdefault(trk, []).append((start, end, note, vel))
                    note_count += 1
            pitch = duration = None

    if not note_count:
        raise ValueError("No note events found.\n" + token_diagnostics(tokens))

    midi = mido.MidiFile(ticks_per_beat=tpq)
    meta = mido.MidiTrack()
    midi.tracks.append(meta)
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm), time=0))
    meta.append(mido.MetaMessage("time_signature", numerator=numerator, denominator=denominator, time=0))
    for idx, program in enumerate(planned):
        # Reserve channel 9 for percussion and skip it for melodic tracks.
        channel = 9 if drums and idx == len(instruments) else idx if idx < 9 else idx + 1
        if channel > 15:
            raise ValueError("MIDI supports at most 15 melodic channels plus drums")
        ev = []
        if channel != 9:
            ev.append((0, 0, mido.Message("program_change", program=program, channel=channel)))
        for start, end, note, vel in collected.get(idx, []):
            ev.append((start, 2, mido.Message("note_on", note=note, velocity=vel, channel=channel)))
            ev.append((end, 1, mido.Message("note_off", note=note, velocity=0, channel=channel)))
        ev.sort(key=lambda e: (e[0], e[1]))
        track = mido.MidiTrack()
        previous = 0
        for tick, _, message in ev:
            track.append(message.copy(time=tick - previous))
            previous = tick
        midi.tracks.append(track)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    midi.save(output)
    return note_count


class Fermata:
    def __init__(self, model_id: str = MODEL_ID, device: Optional[str] = None):
        import torch
        from huggingface_hub import snapshot_download
        from transformers import AutoModelForCausalLM
        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        folder = Path(snapshot_download(model_id, allow_patterns=["config.json", "model.safetensors", "tokenizer/*"]))
        self.vocab = _read_vocabulary(folder / "tokenizer" / "vocab.json")
        self.inverse = {i: t for t, i in self.vocab.items()}
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(str(folder), dtype=dtype).to(self.device).eval()
        if len(self.inverse) != self.model.config.vocab_size:
            raise ValueError("Tokenizer/model vocabulary size mismatch")

    def generate(self, output="output.mid", *, genre="electronic", ensemble="band", bpm=120,
                 key=0, mode="minor", meter="4/4", instruments=(0, 33), drums=True,
                 max_new_tokens=1800, temperature=0.7, top_k=24, top_p=0.95,
                 repetition_penalty=1.12, seed: Optional[int] = None,
                 drum_pitch_correction=False) -> list[str]:
        """Generate token sequence; save raw tokens and best-effort MIDI.

        Returns generated REMI tokens even when MIDI conversion is unsupported.
        """
        torch = self.torch
        if seed is not None:
            torch.manual_seed(seed)
        instruments = list(instruments)
        header = make_header(genre, ensemble, bpm, key, mode, meter, instruments, drums)
        missing = [t for t in header if t not in self.vocab]
        if missing:
            raise ValueError(f"Conditioning tokens absent from vocab: {missing}")
        if max_new_tokens < 1 or len(header) + max_new_tokens > 4096:
            raise ValueError("max_new_tokens must be positive and within 4096-token context")
        ids = torch.tensor([[self.vocab[t] for t in header]], device=self.device)
        eos = self.vocab.get("<EOS>")
        kwargs = dict(max_new_tokens=max_new_tokens, do_sample=True, temperature=temperature,
                      top_k=top_k, top_p=top_p, repetition_penalty=repetition_penalty,
                      pad_token_id=eos if eos is not None else self.vocab["<BOS>"])
        if eos is not None:
            kwargs["eos_token_id"] = eos
        with torch.inference_mode():
            result = self.model.generate(ids, **kwargs)
        tokens = [self.inverse[int(i)] for i in result[0].tolist()]
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".tokens.txt").write_text(" ".join(tokens), encoding="utf-8")
        try:
            count = tokens_to_midi(tokens, str(out), bpm=bpm, instruments=instruments,
                                   drums=drums, meter=meter, drum_pitch_correction=drum_pitch_correction)
            print(f"Saved {out} ({count} decoded notes)")
        except ValueError as exc:
            print(f"MIDI not saved: {exc}\nRaw tokens saved to {out.with_suffix('.tokens.txt')}")
        return tokens


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Generate a symbolic score with Fermata")
    p.add_argument("--output", default="output.mid")
    p.add_argument("--tokens-file", help="Decode an existing .tokens.txt without generating again")
    p.add_argument("--inspect-tokens", help="Show token families and sample of an existing .tokens.txt")
    p.add_argument("--genre", default="electronic", choices=sorted(GENRES))
    p.add_argument("--ensemble", default="band", choices=sorted(ENSEMBLES))
    p.add_argument("--bpm", type=int, default=120)
    p.add_argument("--key", type=int, default=0)
    p.add_argument("--mode", default="minor", choices=sorted(MODES))
    p.add_argument("--meter", default="4/4")
    p.add_argument("--instruments", type=int, nargs="+", default=[0, 33])
    p.add_argument("--no-drums", action="store_true")
    p.add_argument("--max-new-tokens", type=int, default=1800)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--top-k", type=int, default=24)
    p.add_argument("--top-p", type=float, default=0.95)
    p.add_argument("--seed", type=int)
    args = p.parse_args()
    if args.inspect_tokens:
        print(token_diagnostics(Path(args.inspect_tokens).read_text(encoding="utf-8").split()))
    elif args.tokens_file:
        tokens = Path(args.tokens_file).read_text(encoding="utf-8").split()
        notes = tokens_to_midi(tokens, args.output, bpm=args.bpm, instruments=args.instruments,
                               drums=not args.no_drums, meter=args.meter)
        print(f"Saved {args.output}: {notes} notes")
    else:
        Fermata().generate(output=args.output, genre=args.genre, ensemble=args.ensemble,
                       bpm=args.bpm, key=args.key, mode=args.mode, meter=args.meter,
                       instruments=args.instruments, drums=not args.no_drums,
                       max_new_tokens=args.max_new_tokens, temperature=args.temperature,
                       top_k=args.top_k, top_p=args.top_p, seed=args.seed)
