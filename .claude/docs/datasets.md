# Candidate source datasets

Extracted from `draft_plan.md`. All are English — stage 1 decomposes, stage 2
rewrites into Korean.

| Dataset | Scale | Shape | Good for | Caveats |
|---|---|---|---|---|
| [`SALT-NLP/CultureBank`](https://huggingface.co/datasets/SALT-NLP/CultureBank) | 12K | Structured cultural behaviour/norm entries from TikTok + Reddit | Ground-truth cultural descriptors / behaviours | Overlaps with stage 1 extraction — may need deduping against our own output |
| [`allenai/prosocial-dialog`](https://huggingface.co/datasets/allenai/prosocial-dialog) | 58K multi-turn | Social-norm-grounded responses | Korean social norms (존댓말, 위계, 체면) rewriting | Multi-turn — stage 2 needs turn-by-turn handling |
| [`allenai/soda`](https://huggingface.co/datasets/allenai/soda) | 1M | Social dialogues | Scale-up | Volume — plan for sampling, not full run |
| [`teknium/OpenHermes-2.5`](https://huggingface.co/datasets/teknium/OpenHermes-2.5) | 1M | Commonsense QA + assorted | Knowledge-grounded KR rewrites | Schema varies per sample — heavy preprocessing |
| [`allenai/WildChat`](https://huggingface.co/datasets/allenai/WildChat) | 53K | Free-form user/assistant turns | Realistic user prompts | Duplicate user prompts — needs dedup first |
| [`tucnguyen/ShareChat`](https://huggingface.co/datasets/tucnguyen/ShareChat) | 14K | User-assistant with explicit user intent | Intent-tagged rewriting targets | Smaller scale |
| [`google/Synthetic-Persona-Chat`](https://huggingface.co/datasets/google/Synthetic-Persona-Chat) | 11K | Persona-grounded casual dialogue | Persona diversity | Already synthetic — potential overlap with stage 2 personas |

## Internal references (KR-native)

| Resource | Use at |
|---|---|
| AI-Hub — 한국어 어체 변환 데이터셋 ([dataSetSn=287](https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=287)) | Stage 2 few-shot examples for register / 어체 variation |
| 국립국어원 모두의말뭉치 | Cultural replacement sources (proper nouns, honorifics) |
| [`nvidia/Nemotron-Personas-Korea`](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea) | Stage 2 persona scale-up |

## Selection policy

Start with **CultureBank** (already culturally structured) + **prosocial-dialog**
(explicit norm grounding) for the demo. If time permits, add **Synthetic-Persona-Chat**
for style diversity. Skip the 1M-scale sets until stage 1 throughput is validated.
