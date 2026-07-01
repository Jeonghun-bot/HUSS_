def get_policy_diagnosis(benefit_summary, matched_results: dict) -> str:
    """상단에 보여줄 정책 시뮬레이션 한 줄 진단을 만듭니다."""

    current_benefit = benefit_summary.loc[
        benefit_summary["시나리오"] == "현재 상태",
        "월 환산 예상 혜택",
    ].iloc[0]
    best_row = benefit_summary.sort_values("월 환산 예상 혜택", ascending=False).iloc[0]

    new_policy_count = 0
    for scenario_name, result in matched_results.items():
        if scenario_name == "현재 상태" or result["policies"].empty:
            continue
        new_policy_count += int((result["policies"]["match_status"] == "new").sum())

    if new_policy_count > 0:
        return (
            f"현재 월 환산 혜택은 {current_benefit:,.0f}원이며, 생애변화 후 새롭게 검토할 수 있는 "
            f"정책은 {new_policy_count}개입니다. 가장 큰 혜택 가능성은 '{best_row['시나리오']}'에서 나타납니다."
        )

    return (
        f"현재 월 환산 혜택은 {current_benefit:,.0f}원이며, 입력한 미래 계획 기준으로는 "
        "새롭게 추가되는 정책이 많지 않습니다. 소득, 주거, 자녀 수 조건을 다시 확인해보세요."
    )


def build_policy_summary_report(user_profile: dict, benefit_summary, matched_results: dict) -> str:
    """템플릿 기반 문장형 요약 리포트를 생성합니다."""

    current_row = benefit_summary[benefit_summary["시나리오"] == "현재 상태"].iloc[0]
    best_row = benefit_summary.sort_values("월 환산 예상 혜택", ascending=False).iloc[0]

    new_policy_names = []
    needs_check_names = []
    duplicate_names = []

    for scenario_name, result in matched_results.items():
        policies = result["policies"]
        if policies.empty:
            continue

        for _, policy in policies.iterrows():
            if policy["match_status"] == "new":
                new_policy_names.append(f"{scenario_name}: {policy['policy_name']}")
            elif policy["match_status"] == "needs_check":
                needs_check_names.append(f"{scenario_name}: {policy['policy_name']}")
            elif policy["match_status"] == "duplicate":
                duplicate_names.append(f"{scenario_name}: {policy['policy_name']}")

    new_policy_text = ", ".join(new_policy_names[:5]) if new_policy_names else "현재 기준 없음"
    needs_check_text = ", ".join(needs_check_names[:5]) if needs_check_names else "현재 기준 없음"
    duplicate_text = ", ".join(duplicate_names[:5]) if duplicate_names else "현재 기준 없음"

    return f"""
현재 입력 조건은 {user_profile["region"]} 거주, {user_profile["marital_status"]}, 현재 자녀 수
{user_profile["child_count"]}명, 가구 월소득 {user_profile["user_income"] + user_profile["partner_income"]:,.0f}원입니다.

현재 상태에서 규칙 기반으로 계산된 월 환산 예상 혜택은 **{current_row["월 환산 예상 혜택"]:,.0f}원**입니다.
미래 생애변화 시나리오 중에서는 **{best_row["시나리오"]}**에서 월 환산 예상 혜택이
**{best_row["월 환산 예상 혜택"]:,.0f}원**으로 가장 크게 나타납니다.

새롭게 추가될 가능성이 있는 정책은 **{new_policy_text}**입니다.
이미 받고 있거나 중복 가능성이 있는 정책은 **{duplicate_text}**이며,
세부 조건 확인이 필요한 정책은 **{needs_check_text}**입니다.

이 결과는 정책 조건을 단순화한 MVP 시뮬레이션입니다. 실제 신청 전에는 소득 산정 기준,
거주 기간, 자산 기준, 신청 시점, 중복 수급 제한을 공식 사이트에서 반드시 확인해야 합니다.
"""
