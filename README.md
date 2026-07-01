# LifePath AI: 미래 생애변화 기반 맞춤형 정책 추천 시뮬레이터

LifePath AI는 사용자의 현재 조건과 결혼·출산 계획을 입력받아 현재 받을 수 있는 정책뿐 아니라 결혼 후, 첫째 출산 후, 둘째 출산 후에 새롭게 받을 가능성이 있는 정책과 예상 혜택 효과를 비교하는 Streamlit MVP입니다.

## 파일 구조

```text
.
├── app.py
├── data
│   └── policies.csv
├── requirements.txt
├── README.md
└── src
    ├── __init__.py
    ├── policy_matcher.py
    ├── report.py
    └── scenarios.py
```

## 실행 방법

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 핵심 로직

1. 사용자가 현재 조건과 미래 계획을 입력합니다.
2. `src/scenarios.py`가 현재 상태, 결혼 후, 첫째 출산 후, 둘째 출산 후 시나리오를 생성합니다.
3. `data/policies.csv`의 정책 조건을 `src/policy_matcher.py`가 규칙 기반으로 매칭합니다.
4. 정책은 추천, 신규 가능, 중복 가능, 확인 필요 상태로 분류됩니다.
5. 앱은 정책 카드, 신규 정책 목록, 혜택 합계, 정책 적용 전/후 그래프, 타임라인, 요약 리포트를 보여줍니다.

## 주의

정책 데이터와 매칭 규칙은 해커톤 MVP용으로 단순화되어 있습니다. 실제 수급 가능 여부, 금액, 신청 조건은 공식 기관 안내를 확인해야 합니다.
