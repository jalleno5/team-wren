"""Rebuild the editable instrument table from curated creative defaults.

This is a musical policy, not part of TensorFlow/YAMNet. Running this script
overwrites class_instruments.csv, including any manual edits to that table.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Profiles: target kind, zero-based GM program or GM drum pitch, name, role.
PROFILES = {
    "voice": ("program", 53, "Voice Oohs", "voice"),
    "choir": ("program", 52, "Choir Aahs", "voice"),
    "synth_voice": ("program", 54, "Synth Voice", "voice"),
    "whistle": ("program", 78, "Whistle", "wind"),
    "flute": ("program", 73, "Flute", "wind"),
    "clarinet": ("program", 71, "Clarinet", "wind"),
    "sax": ("program", 65, "Alto Sax", "wind"),
    "brass": ("program", 61, "Brass Section", "brass"),
    "horn": ("program", 60, "French Horn", "brass"),
    "trumpet": ("program", 56, "Trumpet", "brass"),
    "trombone": ("program", 57, "Trombone", "brass"),
    "bass": ("program", 33, "Electric Bass (finger)", "bass"),
    "synth_bass": ("program", 38, "Synth Bass 1", "bass"),
    "pad": ("program", 89, "Pad 2 (warm)", "pad"),
    "air": ("program", 99, "FX 4 (atmosphere)", "pad"),
    "strings": ("program", 48, "String Ensemble 1", "strings"),
    "violin": ("program", 40, "Violin", "strings"),
    "cello": ("program", 42, "Cello", "strings"),
    "double_bass": ("program", 43, "Contrabass", "bass"),
    "pizz": ("program", 45, "Pizzicato Strings", "plucked"),
    "guitar": ("program", 24, "Acoustic Guitar (nylon)", "plucked"),
    "electric_guitar": ("program", 27, "Electric Guitar (clean)", "plucked"),
    "distortion_guitar": ("program", 30, "Distortion Guitar", "plucked"),
    "steel_guitar": ("program", 26, "Electric Guitar (jazz)", "plucked"),
    "banjo": ("program", 105, "Banjo", "plucked"),
    "sitar": ("program", 104, "Sitar", "plucked"),
    "zither": ("program", 107, "Koto", "plucked"),
    "harp": ("program", 46, "Orchestral Harp", "plucked"),
    "piano": ("program", 0, "Acoustic Grand Piano", "keys"),
    "electric_piano": ("program", 4, "Electric Piano 1", "keys"),
    "organ": ("program", 19, "Church Organ", "keys"),
    "drawbar_organ": ("program", 16, "Drawbar Organ", "keys"),
    "harpsichord": ("program", 6, "Harpsichord", "keys"),
    "lead": ("program", 80, "Lead 1 (square)", "lead"),
    "saw": ("program", 81, "Lead 2 (sawtooth)", "lead"),
    "sine": ("program", 79, "Ocarina", "wind"),
    "harmonica": ("program", 22, "Harmonica", "wind"),
    "accordion": ("program", 21, "Accordion", "keys"),
    "bagpipe": ("program", 109, "Bag Pipe", "wind"),
    "bell": ("program", 14, "Tubular Bells", "mallet"),
    "glock": ("program", 9, "Glockenspiel", "mallet"),
    "vibes": ("program", 11, "Vibraphone", "mallet"),
    "marimba": ("program", 12, "Marimba", "mallet"),
    "steelpan": ("program", 114, "Steel Drums", "mallet"),
    "timpani": ("program", 47, "Timpani", "bass"),
    "kick": ("drum", 36, "Bass Drum 1", "low_hit"),
    "snare": ("drum", 38, "Acoustic Snare", "snare"),
    "clap": ("drum", 39, "Hand Clap", "snare"),
    "rim": ("drum", 37, "Side Stick", "click"),
    "hat": ("drum", 42, "Closed Hi-Hat", "noise_hit"),
    "open_hat": ("drum", 46, "Open Hi-Hat", "noise_hit"),
    "crash": ("drum", 49, "Crash Cymbal 1", "metal_hit"),
    "ride": ("drum", 51, "Ride Cymbal 1", "metal_hit"),
    "tom": ("drum", 45, "Low Tom", "low_hit"),
    "wood": ("drum", 76, "Hi Wood Block", "click"),
    "tambourine": ("drum", 54, "Tambourine", "shaker"),
    "shaker": ("drum", 70, "Maracas", "shaker"),
    "cowbell": ("drum", 56, "Cowbell", "metal_hit"),
    "triangle": ("drum", 81, "Open Triangle", "metal_hit"),
    "conga": ("drum", 64, "Low Conga", "low_hit"),
    "guiro": ("drum", 74, "Long Guiro", "scrape"),
    "scratch": ("drum", 73, "Short Guiro", "scrape"),
    "claves": ("drum", 75, "Claves", "click"),
}


def build():
    rows = list(csv.DictReader((ROOT / "yamnet_class_map.csv").open(encoding="utf-8")))
    policy = {}

    def assign(start, end, profile):
        for index in range(start, end + 1):
            policy[index] = profile

    # Exhaustive broad creative roles, then finer per-class assignments below.
    for start, end, profile in [
        (0, 34, "voice"), (35, 35, "whistle"), (36, 41, "air"),
        (42, 45, "snare"), (46, 48, "kick"), (49, 55, "conga"),
        (56, 58, "clap"), (59, 60, "kick"), (61, 66, "choir"),
        (67, 105, "clarinet"), (106, 120, "flute"), (121, 130, "shaker"),
        (131, 131, "bass"), (132, 155, "piano"), (156, 178, "snare"),
        (179, 210, "strings"), (211, 276, "piano"),
        (277, 279, "air"), (280, 281, "timpani"), (282, 291, "open_hat"),
        (292, 293, "hat"), (294, 347, "synth_bass"),
        (348, 357, "wood"), (358, 363, "ride"), (364, 371, "open_hat"),
        (372, 381, "rim"), (382, 397, "lead"), (398, 411, "rim"),
        (412, 419, "scratch"), (420, 430, "kick"), (431, 434, "wood"),
        (435, 437, "glock"), (438, 450, "open_hat"), (451, 451, "sine"),
        (452, 453, "open_hat"), (454, 455, "kick"), (456, 458, "lead"),
        (459, 467, "snare"), (468, 474, "scratch"), (475, 479, "glock"),
        (480, 486, "rim"), (487, 487, "bass"), (488, 488, "conga"),
        (489, 489, "tambourine"), (490, 490, "pad"), (491, 492, "lead"),
        (493, 493, "snare"), (494, 494, "pad"), (495, 497, "sine"),
        (498, 499, "lead"), (500, 506, "air"), (507, 509, "hat"),
        (510, 510, "synth_bass"), (511, 511, "distortion_guitar"),
        (512, 512, "sine"), (513, 515, "open_hat"), (516, 517, "synth_bass"),
        (518, 519, "voice"), (520, 520, "air"),
    ]:
        assign(start, end, profile)

    # Instrument labels map directly when General MIDI has an equivalent.
    exact = {
        5: "synth_voice", 12: "air", 24: "choir", 25: "choir", 27: "choir", 28: "choir",
        30: "synth_voice", 32: "pad", 33: "bass", 34: "bass", 57: "rim",
        70: "snare", 72: "horn", 74: "bass", 77: "pad", 79: "hat", 83: "wood",
        86: "trombone", 87: "cowbell", 95: "wood", 102: "brass", 105: "bass",
        111: "sine", 113: "sax", 115: "sine", 116: "open_hat", 120: "rim",
        123: "saw", 124: "saw", 125: "saw", 126: "saw", 128: "conga", 129: "hat",
        134: "guitar", 135: "guitar", 136: "electric_guitar", 137: "bass", 138: "guitar",
        139: "steel_guitar", 140: "wood", 141: "guitar", 142: "banjo", 143: "sitar",
        144: "guitar", 145: "zither", 146: "guitar", 147: "piano", 148: "piano",
        149: "electric_piano", 150: "organ", 151: "drawbar_organ", 152: "drawbar_organ",
        153: "lead", 154: "lead", 155: "harpsichord", 156: "conga", 157: "kick",
        158: "kick", 159: "tom", 160: "snare", 161: "rim", 162: "snare", 163: "kick",
        164: "timpani", 165: "conga", 166: "crash", 167: "hat", 168: "wood",
        169: "tambourine", 170: "shaker", 171: "shaker", 172: "crash", 173: "bell",
        174: "marimba", 175: "marimba", 176: "glock", 177: "vibes", 178: "steelpan",
        180: "brass", 181: "horn", 182: "trumpet", 183: "trombone", 185: "strings",
        186: "violin", 187: "pizz", 188: "cello", 189: "double_bass", 190: "flute",
        191: "flute", 192: "sax", 193: "clarinet", 194: "harp", 195: "bell", 196: "bell",
        197: "tambourine", 198: "glock", 199: "vibes", 200: "bell", 201: "bell",
        202: "bell", 203: "harmonica", 204: "accordion", 205: "bagpipe", 206: "bass",
        207: "horn", 208: "sine", 209: "vibes", 210: "scratch",
        212: "kick", 213: "snare", 214: "electric_guitar", 215: "distortion_guitar",
        216: "distortion_guitar", 217: "distortion_guitar", 218: "electric_guitar",
        219: "electric_guitar", 220: "electric_guitar", 221: "electric_piano", 222: "drawbar_organ",
        223: "bass", 224: "guitar", 225: "sax", 226: "banjo", 227: "bass", 228: "guitar",
        229: "sitar", 230: "sax", 231: "bass", 232: "strings", 233: "choir",
        234: "lead", 235: "kick", 236: "kick", 237: "synth_bass", 238: "snare",
        239: "lead", 240: "lead", 241: "pad", 242: "pad", 243: "conga", 244: "conga",
        245: "guitar", 246: "electric_guitar", 248: "pad", 249: "choir", 250: "choir",
        251: "conga", 252: "conga", 253: "organ", 254: "choir", 255: "zither",
        256: "sitar", 257: "sitar", 258: "brass", 259: "guitar", 260: "electric_guitar",
        264: "bell", 266: "vibes", 267: "lead", 268: "bell", 269: "kick", 270: "organ",
        272: "cello", 273: "harp", 274: "brass", 275: "distortion_guitar", 276: "strings",
        278: "shaker", 284: "marimba", 285: "hat", 291: "conga", 296: "air",
        297: "conga", 302: "brass", 303: "trumpet", 304: "lead", 305: "saw",
        306: "scratch", 307: "violin", 311: "open_hat", 312: "brass", 313: "lead",
        314: "bell", 317: "lead", 318: "lead", 319: "lead", 321: "air", 324: "whistle",
        325: "horn", 326: "wood", 327: "violin", 332: "pad", 333: "tom", 335: "rim",
        336: "wood", 338: "saw", 339: "saw", 341: "saw", 344: "kick", 349: "bell",
        350: "bell", 351: "scratch", 352: "kick", 355: "violin", 358: "cowbell",
        359: "triangle", 360: "wood", 361: "hat", 362: "lead", 363: "saw", 367: "air",
        369: "scratch", 370: "saw", 371: "air", 372: "guiro", 373: "tambourine",
        374: "ride", 375: "rim", 376: "saw", 377: "shaker", 381: "scratch",
        383: "bell", 384: "bell", 385: "bell", 386: "lead", 387: "sine", 388: "sine",
        389: "bell", 392: "saw", 395: "horn", 396: "whistle", 397: "whistle",
        399: "guiro", 403: "guiro", 404: "violin", 405: "rim", 406: "air", 407: "air",
        408: "bell", 409: "guiro", 413: "wood", 414: "snare", 418: "saw", 419: "saw",
        421: "snare", 422: "snare", 423: "snare", 425: "rim", 426: "crash", 427: "snare",
        428: "snare", 437: "crash", 441: "conga", 442: "marimba", 448: "conga",
        459: "tom", 460: "kick", 461: "clap", 463: "crash", 464: "crash", 465: "tom",
        467: "open_hat", 471: "tom", 473: "hat", 474: "guiro", 475: "lead", 478: "cowbell",
        479: "violin", 480: "violin", 481: "shaker", 482: "pad", 483: "wood", 484: "hat",
        486: "wood", 489: "tambourine", 491: "lead", 492: "synth_bass", 499: "synth_bass",
    }
    policy.update(exact)
    assert set(policy) == {int(row["index"]) for row in rows} == set(range(521))
    with (ROOT / "class_instruments.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["index", "mid", "display_name", "kind", "number",
                                                   "instrument", "role", "enabled"])
        writer.writeheader()
        for row in rows:
            kind, number, instrument, role = PROFILES[policy[int(row["index"])]]
            writer.writerow(dict(row, kind=kind, number=number, instrument=instrument,
                                 role=role, enabled="false" if row["display_name"] == "Silence" else "true"))


if __name__ == "__main__":
    build()
