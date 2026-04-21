데이터 파이프라인 목표: 영어 학습 데이터셋을 한국어 학습을 위한 데이터셋으로 자동 변환해주는 데이터 파이프라인
최종목표: k-소버린-한국 문화 이해도가 높은 모델 학습을 위한 데이터셋 생성

인풋: 영어 데이터셋
아웃풋: 한국어 데이터셋 (단순 번역에서 더 할 수 있는 방향)

* fluent 번역 (모국어 st)
* 한국어로 바뀔 때 단순 번역 이상의 문화적이해를 필요로 하는 필드의 데이터셋 선정이 필요


* (기존 방식: 영문 샘플 → 번역 → 끝) 인데 반해, 추천 방식:
    * 영문 샘플 → 한국 상황 intent 추출 → 한국 knowledge base 검색 → 한국 evidence 붙여 재작성 → 추가 한국형 변형 생성
    * ex) 원본
         “How do I reschedule a doctor’s appointment?”
    * 나쁜 한국화
         “의사 예약을 어떻게 다시 잡나요?”
    * 좋은 한국화
         질문 intent를 의료/예약/변경으로 태깅
         → 한국 의료 이용 안내 corpus에서 관련 evidence 검색
         → 한국어 자연화 + 상황화
         → “병원 예약 변경 시 필요한 정보/연락 경로/주의사항” 형태로 재작성



* 전체 loop : 생성 → 검증 → 필터링 (curator) → 평가
    * loop의 성능-효율성 (refinement)



* 목표 데이터셋 선정 (영어 데이터셋)
    * https://huggingface.co/datasets/SALT-NLP/CultureBank
        * TikTok, Reddit에서 추출한 문화적 행동/규범 12K (영어). culturally-aware LLM 학습용으로 설계됨. 각 entry에 cultural descriptor, behavior, context가 구조화되어 있어, 이를 활용할 수 있으나 이전에 있던 phase1과 겹치는 부분이 있을 것(확인 필요) 같아 수정 필요
    * https://huggingface.co/datasets/allenai/prosocial-dialog
        * 58K개 다중턴 영어 대화, 사회 규범 기반 응답. 한국식 사회 규범(존댓말, 위계, 체면 문화)으로 재작성 가능
    * https://huggingface.co/datasets/allenai/soda
        * 사회적 대화 데이터셋 (1M scale)
    * https://huggingface.co/datasets/teknium/OpenHermes-2.5
        * 대규모 데이터셋 (1M) → 상식 기반 QA도 많고, sample마다 구조가 다른 경우도 있어 → preprocessing 필요
    * https://huggingface.co/datasets/allenai/WildChat
        * 53K scale, 중복된 user prompt가 꽤 있는 것으로 보임
    * https://huggingface.co/datasets/tucnguyen/ShareChat
        * user intent를 담고 있는 user-assistant 대화 데이터셋 (14K scale)
    * https://huggingface.co/datasets/google/Synthetic-Persona-Chat
        * persona 기반 일상 대화, 스타일 다양성 (성격/배경 포함) (11K scale)



* 1) 사회언어학적 분해 (LLM 사용)
    * 원본 영어 텍스트를 structured meta data로 변환
    * 감정, 강도, 인터넷용어 마커, 문화적 요소(cultural refs) 마커, 플랫폼,age hierarchy, honorifics 등
        * Analyze this English social media post and return JSON:
            {
              "speech_act": "complaint|brag|question|empathy_seeking|sarcasm|joke|...",
              "register": "intimate|casual|formal|public",
              "emotion": {"type": "...", "intensity": 1-5},
              "cultural_refs": [{"type": "holiday|brand|event|person", "term": "..."}],
              "internet_markers": {
                "laughter": "lol|lmao|rofl|none",
                "emphasis": ["CAPS", "repetition", ...],
                "sarcasm_marker": true/false
              },
              "estimated_age_group": "teen|20s|30s|40plus",
              "platform_fit": ["twitter", "reddit", "instagram", ...]
            }
        * AI-Hub - https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=287
        * 화행(speech act): 불평, 자랑, 질문, 공감 요청, 비꼼, 농담 중 무엇인가
        * 공식성(register): 친구끼리/모르는 사람에게/공적 발화 중 어디인가
        * 감정 강도: 약함/중간/강함
        * 밈·문화 레퍼런스: 특정 사건·인물·작품 인용이 있는가
        * 인터넷 언어 마커: 약어, 이모지, 의도적 오타, 대문자 강조 등
        * 관계성: 화자와 청자의 추정 관계 (친밀/거리감/위계)
* 2) 문화적 요소 치환(LLM)
    * cultural refs로 뽑힌 요소를 한국 문화적 요소로 매핑
    * 참고 source:
        * 국립국어원 모두의말뭉치
    * Tool 사용 이용 고려 필요: 서치 툴을 사용해서 문화적 요소 대체를 할지, 혹은 미리 시환 사전을 구축해두는 것이 좋을지.
        * 사전에 없는 항목을 서칭해서 추가해나가는 방식 
        * → 서치 툴을 사용하는 게 좋아보인다?! 밈 같은거는 시간이 흐르면 빠르게 바뀌니까 데이터도 거기에 맞게 바로바로 바뀔 수 있게 <retrieved> 이런 tag를 달아두는 것도 좋겠. 
        * https://developer.nvidia.com/nemo-retriever
    * CULTURAL_MAP = {
            "thanksgiving": {"ko": "추석", "type": "holiday", "notes": "가족 모임 맥락"},
            "venmo": {"ko": "토스", "type": "service"},
            "prom": {"ko": "졸업식 뒤풀이", "type": "event", "approximate": True},
            "starbucks": {"ko": "스타벅스", "type": "brand", "keep": True},
            ...
        }
* 3) 한국어로 재작성 (LLM)
    * 2,3단계 메타데이터를 사용해 프롬프트에 조건으로 주입해서 번역이 아닌, re-writing.
    * 한국 타겟플랫폼을 명시적으로 지정하는 단계 필요 (how?). 한국어 SNS 말투라고 하면, 평균적인 말투로 수렴
        * ex. 트위터 일상 계정체, 인스타 스토리체, 디시갤러리체 등
        * 한국 Persona로 dataset scale up: https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea
        * 한국어 어체 변환 데이터셋 → AI-Hub - https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=287 이런데서 예시 긁어와서 아래 prompt tuning할 때 few shot으로 넣어주는 것도
    * 예시 (prompt tuning 필요)
        * REWRITE_PROMPT = """
            다음 영어 SNS 글을 한국어 SNS 글로 재작성하세요. 직역 금지.
            
            [원본] {text}
            [화행] {speech_act}
            [공식성] {register}
            [감정] {emotion_type} (강도 {intensity}/5)
            [연령대] {age_group}
            [플랫폼] {target_platform}
            [문화 치환] {cultural_replacements}
            
            규칙:
            - 한국 {target_platform}에서 {age_group}이 실제로 쓸 법한 말투
            - 감정 강도 {intensity}을 정확히 보존 (과장/축소 금지)
            - 문화 치환 사전을 따를 것
            - 인터넷 마커는 표시만 하고 다음 단계에서 처리됨
            """
* 4) 인터넷마커 후처리(룰기반'?)
    * LLM이 만든 한국어 본문에 ㅋㅋ/ㅎㅎ/ㅠㅠ/이모지 같은 마커를 룰로 주입. 메타데이터에 따라 결정적으로 처리:
        * LAUGHTER_MAP = {
                ("lol", 1): "ㅋㅋ",
                ("lol", 2): "ㅋㅋㅋ",
                ("lmao", 3): "ㅋㅋㅋㅋㅋ",
                ("rofl", 5): "ㅋㅋㅋㅋㅋㅋㅋㅋ 개웃기네",
            }
    * 원본: "lololol that's so funny" 
        3단계 LLM 출력 (마커 슬롯 표시): "{LAUGH} 그거 진짜 웃기다" 
        또는 그냥: "그거 진짜 웃기다" 
        4단계 룰 적용 (메타데이터 참조: laughter=lol, intensity=4): 
        최종: "ㅋㅋㅋㅋㅋ 그거 진짜 웃기다"


* 5) 자동 검증
    * 역번역 일치 정도 확인: 한국어 번역본을 영어로 다시 옮겨 원본과 의미 비교 (임베딩 코사인 유사도)
    * 속성 보존도 (원본의 화행, 감정, 강도 보존 여부)
    * 자연스러움 점수 : LLM 평가
    * Consistency / Naturalness / Relevance / Coherence / Fluency → LLM-judge

1. 평가

* LLM judge / Reward Model
* 분포?
* model finetuning + benchmark 결과
        * finetuning pipeline 만들어두기
        * finetuning 할 모델 찾아두기 (소형 모델)


### Require using Nvidia-Stack

#### Essential
    : NIM, NeMo Curator, Data Designer, Guardrails, Nemotron Models, Evaluator
#### Optional
    : Agent Toolkit
#### references:
    - **✨ Curator : https://github.com/NVIDIA-NeMo/Curator https://docs.nvidia.com/nemo/curator/home/welcome**
    - Data Designer : https://github.com/NVIDIA-NeMo/DataDesigner https://docs.nvidia.com/nemo/microservices/latest/about/core-concepts/data-designer.html
    - Evaluator : https://github.com/NVIDIA-NeMo/Evaluator
    - NIM : https://build.nvidia.com/explore/discover
    - Gardrails : https://github.com/NVIDIA-NeMo/Guardrails  https://docs.nvidia.com/nemo/guardrails/latest/index.html
    - Nemo-Retriever : https://github.com/NVIDIA/NeMo-Retriever
    - Agent-Toolkit : https://github.com/NVIDIA/NeMo-Agent-Toolkit https://docs.nvidia.com/nemo/agent-toolkit/latest/index.html
    - Nemo Skills : https://github.com/NVIDIA-NeMo/Skills
    - Models : https://developer.nvidia.com/nemotron
