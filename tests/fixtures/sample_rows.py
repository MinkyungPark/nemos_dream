"""Canned sample rows used across test modules.

These exercise every field in every stage's schema, so changes to
``schemas.py`` that forget to update a consumer fail here first.
"""

from __future__ import annotations

from nemos_dream.schemas import (
    CulturalRef,
    DialogueDecomposed,
    Emotion,
    InternetMarkers,
    MappedRef,
    Persona,
    PersonaEntry,
    PersonaSelectionMeta,
    QualityScores,
    RawInput,
    RejectReason,
    RetrievedPersona,
    RetryAction,
    Scene,
    Speaker,
    Stage1Output,
    Stage2Output,
    Stage3Output,
    Style,
    Turn,
)


def sample_raw() -> RawInput:
    return RawInput(
        id="soda-6027731",
        original_index=6027731,
        dialogue=[
            "Hey Rylea, Google just offered me an internship!",
            "Dude, no way — on your first try? That's huge.",
            "Yeah lmao, I already splurged on a new iPhone to celebrate.",
        ],
        speakers=["Shavon", "Rylea", "Shavon"],
        narrative=(
            "Shavon landed a summer internship at Google and told his best "
            "friend Rylea about it over coffee."
        ),
    )


def sample_stage1() -> Stage1Output:
    raw = sample_raw()
    turns = [
        Turn(index=i, speaker=spk, text=txt)
        for i, (spk, txt) in enumerate(zip(raw.speakers, raw.dialogue, strict=True))
    ]
    return Stage1Output(
        id=raw.id,
        original_index=raw.original_index,
        source_dialogue=turns,
        speakers=[
            Speaker(
                name_en="Shavon",
                role_in_scene="friend",
                gender_hint="male",
                age_group_hint="20s",
                register="casual",
                dominant_emotion=Emotion(type="joy", intensity=5),
                personality_traits=["excitable", "expressive"],
                interests_hints=["tech", "career"],
                occupation_hint="student",
                speech_style_notes="uses internet laughter, informal",
            ),
            Speaker(
                name_en="Rylea",
                role_in_scene="friend",
                gender_hint="unknown",
                age_group_hint="20s",
                register="casual",
                dominant_emotion=Emotion(type="surprise", intensity=4),
                personality_traits=["supportive"],
                interests_hints=[],
                occupation_hint="",
                speech_style_notes="affirming short replies",
            ),
        ],
        scene=Scene(
            narrative_en=raw.narrative,
            setting="cafe",
            relationship_type="friendship",
            topics=["internship", "career", "first_purchase"],
        ),
        dialogue_decomposed=DialogueDecomposed(
            overall_register="casual",
            overall_emotion=Emotion(type="joy", intensity=4),
            speech_acts=["brag", "empathy_seeking"],
            cultural_refs=[
                CulturalRef(type="brand", term="google"),
                CulturalRef(type="brand", term="iphone"),
            ],
        ),
        mapped_refs=[
            MappedRef(
                term="google",
                ko="네이버",
                type="brand",
                source="dict",
                validation=[{"rule": "brand_swap", "ok": True}],
            ),
            MappedRef(
                term="iphone",
                ko="갤럭시",
                type="brand",
                source="web+llm",
                retrieved=True,
                notes="KR flagship analogue for iPhone",
                validation=[{"rule": "brand_swap", "ok": True}],
            ),
        ],
    )


def sample_stage2() -> Stage2Output:
    s1 = sample_stage1()
    # v4 canonical final dialogue — speakers are Korean localised names.
    final = [
        Turn(index=0, speaker="김수현", text="야 윤지야, 나 네이버에서 인턴 제안 받았어!"),
        Turn(index=1, speaker="박윤지", text="뭐?? 첫 도전에? 개쩐다 진짜."),
        Turn(index=2, speaker="김수현", text="ㅋㅋㅋㅋ 기념으로 갤럭시 새로 질렀다."),
    ]
    # v3 deprecated scratch draft — kept populated so the field still has
    # round-trip coverage. New stage-2 writers may leave this empty.
    draft = [
        Turn(index=0, speaker="Shavon", text="야 Rylea, 구글에서 인턴십 제안받았어!"),
        Turn(index=1, speaker="Rylea", text="야 말도 안 돼 — 첫 시도에? 엄청나네."),
        Turn(index=2, speaker="Shavon", text="응 ㅋㅋㅋ 축하로 아이폰 새로 질렀어."),
    ]
    personas = [
        PersonaEntry(
            speaker_index=0,
            speaker_name_en="Shavon",
            retrieved_persona=RetrievedPersona(
                name="김수현",
                age=22,
                age_bucket="20대",
                sex="남자",
                normalized_location="서울-마포구",
                occupation="컴퓨터공학과 학생",
                persona="김수현 씨는 마포구에서 자취하는 22세 컴공 학부생으로…",
                persona_id="kp_0042",
                summary_text="서울-마포구 20대 남자 컴퓨터공학과 학생 김수현 씨…",
                career_goals_and_ambitions="네이버 인턴십을 발판 삼아 주니어 엔지니어로 취업",
                cultural_background="홍대 입구역 근처 원룸촌에서 유튜브와 디스코드 문화에 익숙",
                hobbies_and_interests="피파온라인, 카페 노마드, 트위터 밈 공유",
                skills_and_expertise="파이썬, 리액트, 깃허브 협업",
                extra={"tone_hint": "warm"},
            ),
            selection_metadata=PersonaSelectionMeta(
                candidate_age_buckets=["20s"],
                candidate_gender="male",
                keyword_hints=["대학생", "인턴", "기술"],
                match_score=24.0,
                matched_by_keywords=True,
                selected_random_age_group=False,
                selected_random_gender=False,
            ),
            source_speaker_profile=s1.speakers[0],
        ),
        PersonaEntry(
            speaker_index=1,
            speaker_name_en="Rylea",
            retrieved_persona=RetrievedPersona(
                name="박윤지",
                age=23,
                age_bucket="20대",
                sex="여자",
                normalized_location="서울-성북구",
                occupation="경영학과 학생",
                persona="박윤지 씨는 성북구 본가에서 부모님과 사는 23세 경영 학부생…",
                persona_id="kp_0087",
                summary_text="서울-성북구 20대 여자 경영학과 학생 박윤지 씨…",
                hobbies_and_interests="러닝, 카페 투어, 에세이 필사",
                skills_and_expertise="엑셀, 프레젠테이션, 동아리 기획",
            ),
            source_speaker_profile=s1.speakers[1],
        ),
    ]
    return Stage2Output(
        **s1.model_dump(),
        # v4 canonical
        final_dialogue=final,
        step3_korean_dialogue=final,
        persona=personas,
        # v3 deprecated — populated to keep round-trip field coverage
        korean_dialogue_draft=draft,
        korean_dialogue=final,
        speaker_personas=[
            Persona(
                speaker_ref="Shavon",
                gender="남성",
                age="20대",
                occupation="대학생",
                education="대학 재학",
                marital_status="미혼",
                military_status="미필",
                family_type="1인가구",
                housing="자취",
                major="컴퓨터공학",
                persona_id="kp_0042",
                extra={"tone_hint": "warm"},
            ),
            Persona(
                speaker_ref="Rylea",
                gender="여성",
                age="20대",
                occupation="대학생",
                education="대학 재학",
                marital_status="미혼",
                military_status="해당없음",
                family_type="가족거주",
                housing="본가",
                major="경영학",
            ),
        ],
        speaker_styles=[
            Style(
                speaker_ref="Shavon",
                formality="casual",
                emotion=Emotion(type="joy", intensity=5),
                markers=InternetMarkers(
                    laughter="lmao", emphasis=["exclaim"], sarcasm_marker=False
                ),
                speech_style_notes="20대 남성 대학생, 반말, 인터넷 밈 사용",
                extra={"topic_tag": "career_first_salary"},
            ),
            Style(
                speaker_ref="Rylea",
                formality="casual",
                emotion=Emotion(type="surprise", intensity=4),
                markers=InternetMarkers(
                    laughter="none", emphasis=["repetition"], sarcasm_marker=False
                ),
                speech_style_notes="짧은 감탄 반응, 반말",
            ),
        ],
        translation_meta={
            "target_platform": "thread",
            "target_community": "campus",
            "pass": "first",
        },
    )


def sample_stage3() -> Stage3Output:
    s2 = sample_stage2()
    return Stage3Output(
        **s2.model_dump(),
        quality=QualityScores(
            property_preservation=5,
            naturalness=4,
            cultural_appropriateness=4,
            register_consistency=5,
            persona_style_consistency=4,
            intra_kr_coherence=0.83,
            semantic_cosine=None,
            safety_pass=True,
            pii_pass=True,
            aggregate=4.3,
            reward={"correctness": 0.71, "coherence": 0.78},
            judge_reasoning={
                "naturalness": "Turns flow like a real campus chat; slang fits.",
                "cultural_appropriateness": "Brand swaps (네이버/갤럭시) land naturally.",
            },
        ),
        valid=True,
        reject_reasons=[
            RejectReason(
                stage="stage3.rules",
                rule="turn_count_parity",
                detail="example reject record — ignored because valid=True",
                extra={"expected": 3, "got": 3},
            )
        ],
        retry_actions=[
            RetryAction(
                action="none",
                reason_summary="no remediation needed on this canned row",
            )
        ],
        iter=0,
    )
