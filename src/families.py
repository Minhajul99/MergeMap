"""Family labels for root models.

A root is a model with no declared parent. Its family is decided by its repo
name only (the part after "owner/"), using the ordered list below. The first
pattern that matches wins. A root that matches nothing is "unknown".

The list was built by reading the 400 roots with the most descendants in the
2026-10-22 snapshot. It is frozen: do not change it after results are produced.

Order matters in a few places:
  * "minilm", "clip" and "blip" come first (see the comments in the list).
  * "tinyllama" comes before "llama" (TinyLlama is trained from scratch).
  * "qwen" and "llama" come before "deepseek", so that
    "DeepSeek-R1-Distill-Qwen-7B" is labelled by the model it was distilled into.
  * "roberta" comes before "bert".
"""

import re

# A "word edge": the match must not be glued to other letters or digits.
L = r"(?<![a-z0-9])"   # nothing alphanumeric on the left
R = r"(?![a-z0-9])"    # nothing alphanumeric on the right

FAMILY_PATTERNS = [
    # --- placed first so a later pattern cannot claim them ---
    ("minilm", r"minilm"),                                    # "MiniLM-L3" is not Llama 3
    ("clip", L + r"clip" + R),                                # "clip-vit" is CLIP, not ViT
    ("blip", L + r"blip2?" + R),                              # "blip2-opt" is BLIP-2, not OPT
    # --- large language models ---
    ("tinyllama", r"tinyllama"),
    ("qwen", r"qwen|qwq"),
    ("llama", r"llama|" + L + r"l3(\.[0-9])?" + R),          # "L3-8B", "L3.1-70B"
    ("mistral", r"mistral|mixtral|ministral|codestral|pixtral|devstral|magistral|voxtral"
                r"|nemo(?!tron)|" + L + r"mn" + R),           # "MN-12B" = Mistral Nemo
    ("gemma", r"gemma"),
    ("phi", L + r"phi[-_]?[0-9]"),
    ("deepseek", r"deepseek"),
    ("smollm", r"smollm"),
    ("gpt-oss", r"gpt-oss"),
    ("gpt2", r"gpt-?2" + R),
    ("solar", L + r"solar" + R),
    ("olmo", L + r"olmo" + R),
    ("lfm", L + r"lfm[0-9]"),
    ("nemotron", r"nemotron"),
    ("glm", L + r"glm" + R),
    ("granite", r"granite"),
    ("pythia", r"pythia"),
    ("opt", L + r"opt-[0-9]"),
    # --- image and video generation ---
    ("flux", r"flux"),
    ("stable-diffusion", r"stable-diffusion|sdxl|" + L + r"sd[-_]?(xl|[0-9])"),
    ("krea", L + r"krea" + R),
    ("z-image", r"z-image"),
    ("wan", L + r"wan[0-9]"),
    ("minimax", r"minimax"),
    ("hunyuan", r"hunyuan"),
    # --- speech ---
    ("whisper", r"whisper"),
    ("wav2vec2", r"wav2vec2|w2v-bert|hubert"),
    # --- encoders and sequence-to-sequence models ---
    ("t5", L + r"(flan-?t5|mt5|byt5|t5)" + R),
    ("roberta", r"roberta"),
    ("bert", r"bert"),
    ("bart", L + r"m?bart" + R),
    ("e5", L + r"e5" + R),
    ("bge", L + r"bge" + R),
    ("nllb", r"nllb"),
    ("opus-mt", r"opus-mt"),
    # --- vision ---
    ("vit", L + r"vit" + R + r"|" + L + r"dino"),
    ("resnet", r"resnet"),
    ("swin", L + r"swin"),
    ("detr", L + r"detr" + R),
]

_COMPILED = [(family, re.compile(pattern, re.IGNORECASE)) for family, pattern in FAMILY_PATTERNS]

UNKNOWN = "unknown"
MIXED = "mixed"


def family_of_root(repo_id: str) -> str:
    """Return the family of a root model from its repo id ("owner/name")."""
    name = repo_id.split("/", 1)[-1]
    for family, pattern in _COMPILED:
        if pattern.search(name):
            return family
    return UNKNOWN
