import pandas as pd
import plotly.express as px
import streamlit as st

from src.policy_matcher import (
    calculate_benefit_summary,
    load_policies,
    match_policies_for_scenarios,
)
from src.report import build_policy_summary_report
from src.scenarios import build_life_event_scenarios
from src.validation import validate_user_profile


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
    if child_count == 0:
        youngest_child_age = st.selectbox("가장 어린 자녀 나이", ["해당 없음"], disabled=True)
    else:
        youngest_child_age = st.selectbox("가장 어린 자녀 나이", ["0세", "1세", "2세", "3세 이상", "모름"])
    user_income = st.number_input("본인 월 소득", min_value=0, value=3000000, step=100000)
    partner_income = st.number_input("배우자 또는 예상 배우자 월 소득", min_value=0, value=2800000, step=100000)
    housing_type = st.selectbox("주거 형태", ["월세", "전세", "자가", "기타"])
    home_owner = st.selectbox("주택 보유 여부", ["무주택", "1주택", "다주택"])
    employment_type = st.selectbox("고용 형태", ["정규직", "계약직", "프리랜서", "무직"])

    st.header("현재 받고 있는 정책")
    current_policy_options = policies["policy_name"].drop_duplicates().sort_values().tolist()
    current_policies = st.multiselect("현재 받고 있는 정책", current_policy_options)

    st.header("미래 계획")
    marriage_plan = st.selectbox("결혼 계획", ["없음", "1년 내", "2년 내", "3년 이후"])
    birth_plan = st.selectbox("출산 계획", ["없음", "첫째", "둘째", "추가 자녀"])
    expected_child_count = st.number_input("예상 자녀 수", min_value=0, max_value=4, value=2, step=1)
    birth_timing = st.selectbox("출산 예정 시점", ["미정", "1년 내", "2년 뒤", "3년 이후"])
    dual_income = st.selectbox("맞벌이 유지 여부", ["유지", "일시 중단", "미정"])

user_profile = {
    "age": age,
    "region": region,
    "marital_status": marital_status,
    "child_count": child_count,
    "youngest_child_age": youngest_child_age,
    "child_age": youngest_child_age,
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

profile_warnings = validate_user_profile(user_profile)
if profile_warnings:
    st.subheader("입력값 확인")
    for warning in profile_warnings:
        if warning["level"] == "error":
            st.error(warning["message"])
        else:
            st.warning(warning["message"])

st.subheader("입력 요약")
st.caption(
    f"현재 조건: {region} · {marital_status} · 자녀 {child_count}명 · "
    f"{housing_type} · {home_owner} · {employment_type}"
)
st.caption(
    f"미래 계획: 결혼 {marriage_plan} · 출산 {birth_plan} · "
    f"출산 예정 {birth_timing} · 예상 자녀 수 {expected_child_count}명 · 맞벌이 {dual_income}"
)
st.caption("현재 MVP는 정책 기준일을 고정해 계산하며, 미래 정책 변경 가능성은 반영하지 않습니다.")

# 입력값으로 현재/결혼/출산 시나리오를 만들고 CSV 정책을 규칙 기반으로 매칭합니다.
scenarios = build_life_event_scenarios(user_profile)
matched_results = match_policies_for_scenarios(policies, scenarios, user_profile["current_policies"])
benefit_summary = calculate_benefit_summary(matched_results)

current_new_monthly_total = benefit_summary.loc[
    benefit_summary["시나리오"] == "현재 상태",
    "신규 추천 월 혜택",
].iloc[0]
best_row = benefit_summary.sort_values("1년 기준 단순 합산 지원", ascending=False).iloc[0]
current_result = matched_results.get("현재 상태", {})
current_existing_monthly_total = int(current_result.get("existing_monthly_benefit_total", 0))
current_after_monthly_total = int(current_result.get("after_monthly_benefit_total", 0))
current_existing_one_time_total = int(current_result.get("existing_one_time_benefit_total", 0))
current_new_one_time_total = int(current_result.get("new_one_time_benefit_total", 0))
current_after_one_time_total = int(current_result.get("after_one_time_benefit_total", 0))
current_recommendable_count = int(current_result.get("recommendable_policy_count", 0))
current_needs_check_count = int(current_result.get("needs_check_count", 0))
current_already_receiving_count = int(current_result.get("already_receiving_count", 0))

if current_new_monthly_total == 0:
    diagnosis_text = (
        "입력한 미래 계획 기준으로 새롭게 월 단위로 추가되는 혜택은 없습니다. "
        "확인 필요 정책과 이미 이용 중인 정책을 점검해보세요."
    )
elif current_existing_monthly_total == 0:
    diagnosis_text = (
        f"현재 이용 중인 월 혜택은 없지만, 입력한 조건 기준으로 월 "
        f"{current_new_monthly_total:,.0f}원 수준의 신규 혜택을 확인할 수 있습니다."
    )
else:
    diagnosis_text = (
        f"현재 월 {current_existing_monthly_total:,.0f}원을 이용 중이며, 추가로 월 "
        f"{current_new_monthly_total:,.0f}원 수준의 신규 혜택을 확인할 수 있습니다."
    )
if current_needs_check_count:
    diagnosis_text += " 일부 정책은 자격요건과 신청기한 확인이 필요해 금액 합계에는 포함하지 않았습니다."

st.subheader("1. 한 줄 진단")
st.info(diagnosis_text)

metric_cols = st.columns(3)
metric_cols[0].metric("현재 이용 중 월 혜택", f"{current_existing_monthly_total:,.0f}원")
metric_cols[1].metric("신규 추천 월 혜택", f"{current_new_monthly_total:,.0f}원")
metric_cols[2].metric("추천 반영 후 월 혜택", f"{current_after_monthly_total:,.0f}원")

st.caption(
    f"신규 추천 {current_recommendable_count}개 · 확인 필요 {current_needs_check_count}개 · "
    f"이미 이용 중 {current_already_receiving_count}개 · 분석 정책 {len(policies)}개"
)

with st.expander("상세 요약 보기"):
    detail_cols = st.columns(4)
    detail_cols[0].metric("현재 이용 중 일회성 혜택", f"{current_existing_one_time_total:,.0f}원")
    detail_cols[1].metric("신규 추천 일회성 혜택", f"{current_new_one_time_total:,.0f}원")
    detail_cols[2].metric("추천 반영 후 일회성 혜택", f"{current_after_one_time_total:,.0f}원")
    detail_cols[3].metric("최대 1년 기준 지원", f"{best_row['1년 기준 단순 합산 지원']:,.0f}원", best_row["시나리오"])

    detail_count_cols = st.columns(4)
    detail_count_cols[0].metric("생성 시나리오 수", f"{len(scenarios)}개")
    detail_count_cols[1].metric("현재 상태 추천 가능 정책 수", f"{current_recommendable_count}개")
    detail_count_cols[2].metric("현재 상태 확인 필요 정책 수", f"{current_needs_check_count}개")
    detail_count_cols[3].metric("현재 상태 이미 이용 중 정책 수", f"{current_already_receiving_count}개")

st.subheader("2. 시나리오별 추천 정책 카드")
for scenario_name, result in matched_results.items():
    scenario = result["scenario"]
    matched = result["policies"]
    recommendation_policies = matched[matched["match_status"].isin(["new", "recommended"])]
    needs_check_policies = matched[matched["match_status"] == "needs_check"]
    already_receiving_policies = matched[matched["match_status"] == "already_receiving"]

    expander_title = (
        f"{scenario_name} · 신규 추천 {len(recommendation_policies)}개 · "
        f"확인 필요 {len(needs_check_policies)}개 · 이미 이용 중 {len(already_receiving_policies)}개"
    )

    with st.expander(expander_title, expanded=scenario_name == "현재 상태"):
        scenario_state = "미래 변화 시나리오" if scenario.get("is_future_change", True) else "현재 충족 상태"
        st.caption(
            f"{scenario_state} · 혼인 상태: {scenario['marital_status']} · 자녀 수: {scenario['child_count']}명 · "
            f"가장 어린 자녀 나이: {scenario.get('youngest_child_age', '해당 없음')} · "
            f"가구 월소득: {scenario['household_income']:,.0f}원 · 주거: {scenario['housing_type']} · "
            f"주택: {scenario['home_owner']} · "
            f"{'미래 계획 반영' if scenario.get('generated_by_future_plan') else '현재 조건 기준'}"
        )
        st.caption(scenario.get("plan_note", ""))

        st.markdown("**신규 추천 정책**")
        if recommendation_policies.empty:
            st.write("이 시나리오에서 새롭게 추천할 정책은 없습니다.")
        else:
            card_cols = st.columns(2)
            for index, policy in recommendation_policies.reset_index(drop=True).iterrows():
                with card_cols[index % 2]:
                    status_label = {
                        "recommended": "추천 가능",
                        "new": "새롭게 추가 가능",
                    }.get(policy["match_status"], "추천 가능")

                    with st.container(border=True):
                        st.markdown(f"**{policy['policy_name']}**")
                        st.caption(f"{policy['category']} · {status_label}")
                        st.write(f"혜택 유형: **{policy['benefit_type']}**")
                        st.write(f"혜택 금액: **{policy['benefit_amount']:,.0f}원**")
                        st.write(
                            "추천 이유: "
                            f"{policy['match_reasons'] if policy['match_reasons'] else '입력 조건과 정책 기본 조건이 일치합니다.'}"
                        )
                        st.caption(policy["description"])
                        st.link_button("공식 링크", policy["official_site"])

        st.markdown("**금액 미산정 확인 후보**")
        st.caption("확인 필요 정책은 실제 수급 가능 여부와 금액 산정에 추가 정보가 필요한 정책입니다. 본 MVP에서는 금액 합계에 포함하지 않았습니다.")
        if needs_check_policies.empty:
            st.write("이 시나리오에서 금액 확인이 필요한 정책은 없습니다.")
        else:
            st.dataframe(
                needs_check_policies[
                    ["policy_name", "category", "benefit_type", "check_reasons", "official_site"]
                ].rename(
                    columns={
                        "policy_name": "정책명",
                        "category": "분야",
                        "benefit_type": "혜택 유형",
                        "check_reasons": "확인 사유",
                        "official_site": "공식 사이트",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("**이미 이용 중인 정책**")
        st.caption(
            "이미 이용 중인 정책은 신규 추천 정책 수와 신규 혜택 합계에서는 제외하지만, 현재 수혜 기준값에는 반영했습니다. "
            "단, 금액 확인이 필요한 이미 이용 중 정책은 현재 수혜 기준 금액에 포함하지 않았습니다."
        )
        if already_receiving_policies.empty:
            st.write("이 시나리오에서 이미 이용 중으로 표시된 정책은 없습니다.")
        else:
            st.dataframe(
                already_receiving_policies[
                    ["policy_name", "category", "benefit_type", "benefit_amount", "official_site"]
                ].rename(
                    columns={
                        "policy_name": "정책명",
                        "category": "분야",
                        "benefit_type": "혜택 유형",
                        "benefit_amount": "혜택 금액",
                        "official_site": "공식 사이트",
                    }
                ),
                use_container_width=True,
                hide_index=True,
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
summary_core_columns = [
    "시나리오",
    "현재 이용 중 혜택",
    "신규 추천 월 혜택",
    "추가 추천 반영 후",
]
summary_detail_columns = [
    "시나리오",
    "현재 이용 중 혜택",
    "신규 추천 월 혜택",
    "추가 추천 반영 후",
    "현재 이용 중 일회성 혜택",
    "신규 추천 일회성 혜택",
    "추천 반영 후 일회성 혜택",
    "1년 기준 단순 합산 지원",
    "확인 필요 정책 수",
    "이미 이용 중 정책 수",
    "신규 정책 수",
    "추천 가능 정책 수",
]
for column in [
    "현재 이용 중 혜택",
    "신규 추천 월 혜택",
    "추가 추천 반영 후",
    "현재 이용 중 일회성 혜택",
    "신규 추천 일회성 혜택",
    "추천 반영 후 일회성 혜택",
    "1년 기준 단순 합산 지원",
]:
    summary_display[column] = summary_display[column].map(lambda value: f"{value:,.0f}원")
st.dataframe(summary_display[summary_core_columns], use_container_width=True, hide_index=True)

with st.expander("시나리오별 상세 지표 보기"):
    st.dataframe(summary_display[summary_detail_columns], use_container_width=True, hide_index=True)

with st.expander("참고용 장기 누적액 보기"):
    long_term_display = benefit_summary[["시나리오", "참고용 장기 누적액"]].copy()
    long_term_display["참고용 장기 누적액"] = long_term_display["참고용 장기 누적액"].map(
        lambda value: f"{value:,.0f}원"
    )
    st.caption("정책별 전체 지원기간을 단순 합산한 값입니다. 중복 수급 제한과 자격 변동은 반영하지 않습니다.")
    st.dataframe(long_term_display, use_container_width=True, hide_index=True)

st.subheader("4-1. 금액 미산정 확인 후보")
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

st.subheader("5. 현재 수혜 기준과 추가 추천 반영 효과 비교")
comparison_df = pd.concat(
    [
        benefit_summary[["시나리오", "현재 이용 중 혜택"]].rename(columns={"현재 이용 중 혜택": "금액"}).assign(
            구분="현재 이용 중 혜택"
        ),
        benefit_summary[["시나리오", "추가 추천 반영 후"]].rename(columns={"추가 추천 반영 후": "금액"}).assign(
            구분="신규 추천 반영 후"
        ),
        benefit_summary[["시나리오", "월 추가 효과"]].rename(columns={"월 추가 효과": "금액"}).assign(
            구분="추가 효과"
        ),
    ],
    ignore_index=True,
)
comparison_fig = px.bar(
    comparison_df,
    x="시나리오",
    y="금액",
    color="구분",
    barmode="group",
    title="시나리오별 현재 이용 중 혜택과 신규 추천 반영 후 월 혜택",
)
st.plotly_chart(comparison_fig, use_container_width=True)

additional_effect_display = benefit_summary[["시나리오", "현재 이용 중 혜택", "신규 추천 월 혜택", "추가 추천 반영 후", "월 추가 효과"]].copy()
additional_effect_display = additional_effect_display.rename(columns={"추가 추천 반영 후": "신규 추천 반영 후"})
for column in ["현재 이용 중 혜택", "신규 추천 월 혜택", "신규 추천 반영 후", "월 추가 효과"]:
    additional_effect_display[column] = additional_effect_display[column].map(lambda value: f"{value:,.0f}원")
st.dataframe(additional_effect_display, use_container_width=True, hide_index=True)

st.subheader("6. 정책 변화 타임라인")
timeline_rows = []
for order, (scenario_name, result) in enumerate(matched_results.items(), start=1):
    policies_for_scenario = result["policies"]
    timeline_rows.append(
        {
            "순서": order,
            "시나리오": scenario_name,
            "신규 추천 정책 수": int(policies_for_scenario["match_status"].isin(["new", "recommended"]).sum())
            if not policies_for_scenario.empty
            else 0,
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
    y="신규 추천 정책 수",
    text="시나리오",
    markers=True,
    title="생애변화에 따른 신규 추천 정책 수 변화",
)
timeline_fig.update_traces(textposition="top center")
st.plotly_chart(timeline_fig, use_container_width=True)
st.dataframe(timeline_df, use_container_width=True, hide_index=True)

st.subheader("7. 문장형 요약 리포트")
st.markdown(build_policy_summary_report(user_profile, benefit_summary, matched_results))

st.divider()
st.caption(
    "안내: 본 서비스는 해커톤 MVP 데모이며, 정책 데이터와 매칭 규칙을 단순화해 시뮬레이션합니다. "
    "본 결과는 정책 탐색을 위한 참고용이며, 실제 수급 가능 여부와 정확한 금액은 공식 기관에서 반드시 확인해야 합니다. "
    "실제 수급 가능 여부, 지원 금액, 신청 조건을 보장하지 않으며 반드시 공식 기관 안내를 확인해야 합니다. "
    "확인 필요 정책은 실제 수급 가능 여부와 금액 산정에 추가 정보가 필요한 정책입니다. "
    "본 MVP에서는 금액 합계에 포함하지 않았습니다. "
    "최종 신청 가능 여부와 정확한 금액은 공식 기관에서 반드시 확인해야 합니다."
)
