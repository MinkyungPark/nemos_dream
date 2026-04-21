"""Canned sample rows used across test modules.

These exercise every field in every stage's schema, so changes to
``schemas.py`` that forget to update a consumer fail here first.
"""

from __future__ import annotations

from nemos_dream.schemas import (
    CulturalRef,
    Decomposed,
    Emotion,
    InternetMarkers,
    MappedRef,
    QualityScores,
    RawInput,
    RewriteMeta,
    Stage1Output,
    Stage2Output,
    Stage3Output,
)


def sample_raw() -> RawInput:
    return RawInput(
        id="d05",
        source_text=(
            "bro literally got his first paycheck from his summer internship at Google "
            "and already splurged on a new iphone lmao"
        ),
    )


def sample_stage1() -> Stage1Output:
    raw = sample_raw()
    return Stage1Output(
        id=raw.id,
        source_text=raw.source_text,
        decomposed=Decomposed(
            source_text=raw.source_text,
            speech_act="brag",
            register="casual",
            emotion=Emotion(type="joy", intensity=4),
            cultural_refs=[
                CulturalRef(type="brand", term="google"),
                CulturalRef(type="brand", term="iphone"),
            ],
            internet_markers=InternetMarkers(
                laughter="lmao", emphasis=[], sarcasm_marker=False
            ),
            estimated_age_group="20s",
            platform_fit=["twitter", "instagram"],
        ),
        mapped_refs=[
            MappedRef(term="google", ko="네이버", type="brand", source="dict"),
            MappedRef(
                term="iphone",
                ko="갤럭시",
                type="brand",
                source="web+llm",
                retrieved=True,
                notes="KR flagship analogue for iPhone",
            ),
        ],
    )


def sample_stage2() -> Stage2Output:
    s1 = sample_stage1()
    return Stage2Output(
        **s1.model_dump(),
        ko_text_pre_marker="친구가 네이버 인턴십 첫 월급 받자마자 갤럭시 새 거 질렀다",
        ko_text="친구가 네이버 인턴십 첫 월급 받자마자 갤럭시 새 거 질렀다 ㅋㅋㅋㅋㅋ",
        rewrite_meta=RewriteMeta(
            target_platform="twitter",
            target_age_group="20s",
            target_community="campus",
            target_gender_style="neutral",
            persona_id="kp_0042",
        ),
    )


def sample_stage3() -> Stage3Output:
    s2 = sample_stage2()
    return Stage3Output(
        **s2.model_dump(),
        quality=QualityScores(
            semantic_cosine=0.82,
            property_preservation=5,
            naturalness=4,
            cultural_appropriateness=4,
            register_consistency=5,
            safety_pass=True,
            pii_pass=True,
            aggregate=4.3,
            reward={"correctness": 0.71, "coherence": 0.78},
        ),
        valid=True,
        reject_reasons=[],
    )
