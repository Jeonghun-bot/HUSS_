import pandas as pd
import plotly.express as px
import streamlit as st

from src.policy_matcher import (
    calculate_benefit_summary,
    load_policies,
    match_policies_for_scenarios,
)
from src.report import build_policy_summary_report, get_policy_diagnosis
from src.scenarios import build_life_event_scenarios


st.set_page_config(page_title="LifePath AI", page_icon="🧭", layout="wide")

st.title("LifePath AI: 미래 생애변화 기반 맞춤형 정책 추천 시뮬레이터")
st.caption("결혼·출산이라는 미래 변화에 따라 정책 수혜 가능성이 어떻게 달라지는지 미리 비교합니다.")

policies = load_policies("data/policies.csv")

with st.sidebar:
    st.header("현재 조건")
    age = st.number_input("나이", min_value=19, max_value=59, value=30, step=1)
    region = st.selectbox("거주 지역", ["서울", "경기", "부산"])
    marital_status = st.selectbox("현재 혼인 상태", ["미혼", "기혼"])
    child_count = st.number_input("현재 자녀 수", min_value=0, max_value=5, value=0, step=1)
    user_income = st.number_input("본인 월 소득", min_value=0, value=3000000, step=100000)
    partner_income = st.number_input("배우자 또는 예상 배우자 월 소득", min_value=0, value=2800000, step=100000)
    housing_type = st.selectbox("주거 형태", ["월세", "전세", "자가", "기타"])
    home_owner = st.selectbox("주택 보유 여부", ["무주택", "1주택", "다주택"])
    employment_type = st.selectbox("고용 형태", ["정규직", "계약직", "프리랜서", "무직"])

    st.header("현재 받고 있는 정책")
    current_policy_options = policies["policy_name"].drop_duplicates().sort_values().tolist()
    current_policies = st.multiselect("현재 받고 있는 정책", current_policy_options)

    st.header("미래 계획")
    marriage_plan = st.selectbox("결혼 계획", ["없음", "1년 이내", "2년 이내", "3년 이후"])
    birth_plan = st.selectbox("출산 계획", ["없음", "1년 이내", "2년 이내", "3년 이후"])
    expected_child_count = st.number_input("예상 자녀 수", min_value=0, max_value=4, value=2, step=1)
    birth_timing = st.selectbox("출산 예정 시점", ["미정", "1년 이내", "2년 이내", "3년 이후"])
    dual_income = st.selectbox("맞벌이 유지 여부", ["유지", "일시 중단", "미정"])

user_profile = {
    "age": age,
    "region": region,
    "marital_status": marital_status,
    "child_count": child_count,
    "user_income": user_income,
    "partner_income": partner_income,
    "housing_type": housing_type,
    "home_owner": home_owner,
    "employment_type": employment_type,
    "current_policies": current_policies,
    "marriage_plan": marriage_plan,
    "birth_plan": birth_plan,
    "expected_child_count": expected_child_count,
    "birth_timing": birth_timing,
    "dual_income": dual_income,
}

# 입력값으로 현재/결혼/출산 시나리오를 만들고 CSV 정책을 규칙 기반으로 매칭합니다.
scenarios = build_life_event_scenarios(user_profile)
matched_results = match_policies_for_scenarios(policies, scenarios, user_profile["current_policies"])
benefit_summary = calculate_benefit_summary(matched_results)

current_total = benefit_summary.loc[
    benefit_summary["시나리오"] == "현재 상태",
    "예상 월 지원 효과",
].iloc[0]
best_row = benefit_summary.sort_values("1년 기준 단순 합산 지원", ascending=False).iloc[0]

st.subheader("1. 한 줄 진단")
st.info(get_policy_diagnosis(benefit_summary, matched_results))

metric_cols = st.columns(4)
metric_cols[0].metric("분석 정책 수", f"{len(policies)}개")
metric_cols[1].metric("현재 예상 월 지원 효과", f"{current_total:,.0f}원")
metric_cols[2].metric("최대 1년 기준 지원", f"{best_row['1년 기준 단순 합산 지원']:,.0f}원", best_row["시나리오"])
metric_cols[3].metric("생성 시나리오", f"{len(scenarios)}개")

st.subheader("2. 시나리오별 추천 정책 카드")
for scenario_name, result in matched_results.items():
    scenario = result["scenario"]
    matched = result["policies"]

    with st.expander(f"{scenario_name} · {len(matched)}개 정책 매칭", expanded=scenario_name == "현재 상태"):
        scenario_state = "미래 변화 시나리오" if scenario.get("is_future_change", True) else "현재 충족 상태"
        st.caption(
            f"{scenario_state} · 혼인 상태: {scenario['marital_status']} · 자녀 수: {scenario['child_count']}명 · "
            f"가구 월소득: {scenario['household_income']:,.0f}원 · 주거: {scenario['housing_type']} · "
            f"주택: {scenario['home_owner']}"
        )

        if matched.empty:
            st.write("이 시나리오에서 바로 추천할 정책이 없습니다.")
            continue

        card_cols = st.columns(2)
        for index, policy in matched.iterrows():
            with card_cols[index % 2]:
                status_label = {
                    "recommended": "현재/미래 추천",
                    "new": "새롭게 추가 가능",
                    "already_receiving": "이미 이용 중",
                    "duplicate": "이미 수급 또는 중복",
                    "needs_check": "확인 필요",
                }.get(policy["match_status"], "확인 필요")

                st.markdown(
                    f"""
**{policy["policy_name"]}**

- 구분: {policy["category"]} · {status_label}
- 생애 이벤트: {policy["life_event"]}
- 혜택: {policy["benefit_type"]} {policy["benefit_amount"]:,.0f}원
- 기간: {int(policy["benefit_period_months"])}개월
- 설명: {policy["description"]}
- 안내: 실제 수급 여부와 금액은 소득, 재산, 이용 서비스, 중복 수급 가능 여부에 따라 달라질 수 있습니다.
- 확인: 본 결과는 정책 탐색을 위한 참고용이며, 최종 신청 가능 여부는 공식 기관에서 확인해야 합니다.
- 공식 사이트: {policy["official_site"]}
"""
                )

st.subheader("3. 현재 대비 새롭게 추가되는 정책 목록")
new_policy_rows = []
for scenario_name, result in matched_results.items():
    if scenario_name == "현재 상태":
        continue
    new_policies = result["policies"][result["policies"]["match_status"] == "new"]
    for _, policy in new_policies.iterrows():
        new_policy_rows.append(
            {
                "시나리오": scenario_name,
                "정책명": policy["policy_name"],
                "분야": policy["category"],
                "혜택 유형": policy["benefit_type"],
                "혜택 금액": policy["benefit_amount"],
                "설명": policy["description"],
            }
        )

if new_policy_rows:
    st.dataframe(pd.DataFrame(new_policy_rows), use_container_width=True, hide_index=True)
else:
    st.write("현재 입력값 기준으로 새롭게 추가되는 정책은 아직 없습니다.")

st.subheader("4. 보수적 혜택 추정")
summary_display = benefit_summary.copy()
summary_columns = [
    "시나리오",
    "예상 월 지원 효과",
    "초기 일회성 지원",
    "1년 기준 단순 합산 지원",
    "확인 필요 정책 수",
    "신규 정책 수",
]
for column in ["예상 월 지원 효과", "초기 일회성 지원", "1년 기준 단순 합산 지원"]:
    summary_display[column] = summary_display[column].map(lambda value: f"{value:,.0f}원")
st.dataframe(summary_display[summary_columns], use_container_width=True, hide_index=True)

with st.expander("참고용 장기 누적액 보기"):
    long_term_display = benefit_summary[["시나리오", "참고용 장기 누적액"]].copy()
    long_term_display["참고용 장기 누적액"] = long_term_display["참고용 장기 누적액"].map(
        lambda value: f"{value:,.0f}원"
    )
    st.caption("정책별 전체 지원기간을 단순 합산한 값입니다. 중복 수급 제한과 자격 변동은 반영하지 않습니다.")
    st.dataframe(long_term_display, use_container_width=True, hide_index=True)

st.subheader("4-1. 금액 확인 필요 정책")
needs_check_rows = []
for scenario_name, result in matched_results.items():
    needs_check_policies = result["policies"][result["policies"]["match_status"] == "needs_check"]
    for _, policy in needs_check_policies.iterrows():
        needs_check_rows.append(
            {
                "시나리오": scenario_name,
                "정책명": policy["policy_name"],
                "분야": policy["category"],
                "확인 사유": policy["check_reasons"],
                "공식 사이트": policy["official_site"],
            }
        )

if needs_check_rows:
    st.dataframe(pd.DataFrame(needs_check_rows), use_container_width=True, hide_index=True)
else:
    st.write("현재 입력값 기준으로 금액 확인이 필요한 정책은 없습니다.")

st.subheader("5. 정책 적용 전/후 금전 효과 비교")
comparison_df = benefit_summary.melt(
    id_vars=["시나리오"],
    value_vars=["정책 적용 전 기준값", "예상 월 지원 효과", "정책 적용 후 효과"],
    var_name="구분",
    value_name="금액",
)
comparison_fig = px.bar(
    comparison_df,
    x="시나리오",
    y="금액",
    color="구분",
    barmode="group",
    title="시나리오별 정책 적용 전/후 예상 월 지원 효과",
)
st.plotly_chart(comparison_fig, use_container_width=True)

st.subheader("6. 정책 변화 타임라인")
timeline_rows = []
for order, (scenario_name, result) in enumerate(matched_results.items(), start=1):
    policies_for_scenario = result["policies"]
    timeline_rows.append(
        {
            "순서": order,
            "시나리오": scenario_name,
            "추천 정책 수": len(policies_for_scenario),
            "새롭게 추가 가능": int((policies_for_scenario["match_status"] == "new").sum())
            if not policies_for_scenario.empty
            else 0,
            "이미 이용 중": int((policies_for_scenario["match_status"] == "already_receiving").sum())
            if not policies_for_scenario.empty
            else 0,
            "확인 필요": int((policies_for_scenario["match_status"] == "needs_check").sum())
            if not policies_for_scenario.empty
            else 0,
        }
    )

timeline_df = pd.DataFrame(timeline_rows)
timeline_fig = px.line(
    timeline_df,
    x="순서",
    y="추천 정책 수",
    text="시나리오",
    markers=True,
    title="생애변화에 따른 추천 정책 수 변화",
)
timeline_fig.update_traces(textposition="top center")
st.plotly_chart(timeline_fig, use_container_width=True)
st.dataframe(timeline_df, use_container_width=True, hide_index=True)

st.subheader("7. 문장형 요약 리포트")
st.markdown(build_policy_summary_report(user_profile, benefit_summary, matched_results))

st.divider()
st.caption(
    "안내: 본 서비스는 해커톤 MVP 데모이며, 정책 데이터와 매칭 규칙을 단순화해 시뮬레이션합니다. "
    "실제 수급 가능 여부, 지원 금액, 신청 조건을 보장하지 않으며 반드시 공식 기관 안내를 확인해야 합니다."
)
