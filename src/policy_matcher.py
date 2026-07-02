from pathlib import Path

import pandas as pd


ANY_VALUES = {"전체", "무관", "상관없음", "any", "ANY", ""}
BENEFIT_TYPES = {"월지급", "일회성", "월환산", "확인필요"}

RESULT_COLUMNS = [
    "policy_name",
    "category",
    "life_event",
    "region",
    "min_age",
    "max_age",
    "marital_status",
    "min_child_count",
    "max_child_count",
    "min_income",
    "max_income",
    "housing_type",
    "home_owner",
    "employment_type",
    "benefit_type",
    "benefit_amount",
    "benefit_period_months",
    "description",
    "eligibility_summary",
    "official_site",
    "source_name",
    "source_date",
    "match_status",
    "match_reasons",
    "check_reasons",
    "child_age_check",
    "timing_check",
    "included_in_yearly_total",
    "included_in_existing_monthly_total",
    "included_in_existing_one_time_total",
    "included_in_new_monthly_total",
    "included_in_new_one_time_total",
    "included_in_after_monthly_total",
    "included_in_after_one_time_total",
]


def load_policies(path: str) -> pd.DataFrame:
    """CSV 정책 데이터를 읽고 새 스키마의 숫자 컬럼을 안전하게 정리합니다."""

    policies = pd.read_csv(Path(path))
    numeric_columns = [
        "min_age",
        "max_age",
        "min_income",
        "max_income",
        "min_child_count",
        "max_child_count",
        "benefit_amount",
        "benefit_period_months",
    ]

    for column in numeric_columns:
        if column in policies.columns:
            policies[column] = pd.to_numeric(policies[column], errors="coerce").fillna(0).astype(int)

    text_columns = [column for column in policies.columns if column not in numeric_columns]
    for column in text_columns:
        policies[column] = policies[column].fillna("").astype(str)

    return policies


def match_policies(user_profile: dict, scenario: dict, policies_df: pd.DataFrame) -> pd.DataFrame:
    """
    사용자 입력값과 하나의 생애 시나리오를 기준으로 정책 후보를 매칭합니다.

    not_matched 정책은 앱의 추천 카드에는 노출하지 않지만, 내부 상태값은
    _evaluate_policy에서 명확하게 구분합니다.
    """

    current_policy_names = set(user_profile.get("current_policies", []))
    current_matched_names = set(user_profile.get("_current_matched_policy_names", []))
    rows = []

    for _, policy in policies_df.iterrows():
        evaluation = _evaluate_policy(policy, scenario)
        if evaluation["match_status"] == "not_matched":
            continue

        policy_dict = policy.to_dict()
        policy_name = policy_dict["policy_name"]

        if policy_name in current_policy_names:
            status = "already_receiving"
        elif evaluation["match_status"] == "needs_check":
            status = "needs_check"
        elif scenario.get("is_future_change", True) and policy_name not in current_matched_names:
            status = "new"
        else:
            status = "recommended"

        policy_dict["match_status"] = status
        policy_dict["match_reasons"] = "; ".join(evaluation["match_reasons"])
        policy_dict["check_reasons"] = "; ".join(evaluation["check_reasons"])
        policy_dict["child_age_check"] = evaluation["child_age_check"]
        policy_dict["timing_check"] = evaluation["timing_check"]
        rows.append(policy_dict)

    frame = _build_result_frame(rows)
    frame["included_in_yearly_total"] = frame.apply(_is_included_in_yearly_total, axis=1)
    frame["included_in_existing_monthly_total"] = frame.apply(_is_included_in_existing_monthly_total, axis=1)
    frame["included_in_existing_one_time_total"] = frame.apply(_is_included_in_existing_one_time_total, axis=1)
    frame["included_in_new_monthly_total"] = frame.apply(_is_included_in_new_monthly_total, axis=1)
    frame["included_in_new_one_time_total"] = frame.apply(_is_included_in_new_one_time_total, axis=1)
    frame["included_in_after_monthly_total"] = (
        frame["included_in_existing_monthly_total"] | frame["included_in_new_monthly_total"]
    )
    frame["included_in_after_one_time_total"] = (
        frame["included_in_existing_one_time_total"] | frame["included_in_new_one_time_total"]
    )
    return frame


def match_policies_for_scenarios(
    policies: pd.DataFrame,
    scenarios: list[dict],
    current_policy_names: list[str],
) -> dict:
    """각 시나리오별 정책 후보와 혜택 요약값을 앱이 쓰는 구조로 반환합니다."""

    results = {}
    current_matched_names = set(current_policy_names)
    user_profile = {"current_policies": current_policy_names}

    for scenario in scenarios:
        user_profile["_current_matched_policy_names"] = current_matched_names
        matched_df = match_policies(user_profile, scenario, policies)

        if scenario["name"] == "현재 상태":
            current_matched_names |= set(matched_df["policy_name"].tolist())

        totals = _calculate_totals(matched_df)
        results[scenario["name"]] = {
            "scenario": scenario,
            "policies": matched_df,
            "monthly_benefit_total": totals["monthly_benefit_total"],
            "one_time_benefit_total": totals["one_time_benefit_total"],
            "monthly_equivalent_total": totals["monthly_equivalent_total"],
            "existing_monthly_benefit_total": totals["existing_monthly_benefit_total"],
            "new_monthly_benefit_total": totals["new_monthly_benefit_total"],
            "after_monthly_benefit_total": totals["after_monthly_benefit_total"],
            "existing_one_time_benefit_total": totals["existing_one_time_benefit_total"],
            "new_one_time_benefit_total": totals["new_one_time_benefit_total"],
            "after_one_time_benefit_total": totals["after_one_time_benefit_total"],
            "one_year_benefit_total": totals["one_year_benefit_total"],
            "long_term_reference_total": totals["long_term_reference_total"],
            "total_benefit": totals["total_benefit"],
            "needs_check_count": int((matched_df["match_status"] == "needs_check").sum()),
            "new_policy_count": int((matched_df["match_status"] == "new").sum()),
            "recommendable_policy_count": int(matched_df["match_status"].isin(["new", "recommended"]).sum()),
            "already_receiving_count": int((matched_df["match_status"] == "already_receiving").sum()),
        }

    return results


def calculate_benefit_summary(matched_results: dict) -> pd.DataFrame:
    """시나리오별 월 지원, 일회성 지원, 1년 기준 지원액을 계산합니다."""

    rows = []

    for scenario_name, result in matched_results.items():
        existing_monthly_total = int(result.get("existing_monthly_benefit_total", 0))
        new_monthly_total = int(result.get("new_monthly_benefit_total", 0))
        after_monthly_total = int(result.get("after_monthly_benefit_total", 0))
        existing_one_time_total = int(result.get("existing_one_time_benefit_total", 0))
        new_one_time_total = int(result.get("new_one_time_benefit_total", 0))
        after_one_time_total = int(result.get("after_one_time_benefit_total", 0))
        one_year_benefit_total = int(result.get("one_year_benefit_total", 0))
        long_term_reference_total = int(result.get("long_term_reference_total", 0))
        rows.append(
            {
                "시나리오": scenario_name,
                "현재 이용 중 혜택": existing_monthly_total,
                "신규 추천 월 혜택": new_monthly_total,
                "추가 추천 반영 후": after_monthly_total,
                "월 추가 효과": new_monthly_total,
                "현재 이용 중 일회성 혜택": existing_one_time_total,
                "신규 추천 일회성 혜택": new_one_time_total,
                "추천 반영 후 일회성 혜택": after_one_time_total,
                "일회성 추가 효과": new_one_time_total,
                "예상 월 지원 효과": new_monthly_total,
                "초기 일회성 지원": new_one_time_total,
                "1년 기준 단순 합산 지원": one_year_benefit_total,
                "참고용 장기 누적액": long_term_reference_total,
                "월 환산 예상 혜택": new_monthly_total,
                "일회성 예상 혜택": new_one_time_total,
                "정책 적용 전 기준값": existing_monthly_total,
                "정책 적용 후 효과": after_monthly_total,
                "확인 필요 정책 수": int(result.get("needs_check_count", 0)),
                "신규 정책 수": int(result.get("new_policy_count", 0)),
                "추천 가능 정책 수": int(result.get("recommendable_policy_count", 0)),
                "이미 이용 중 정책 수": int(result.get("already_receiving_count", 0)),
            }
        )

    return pd.DataFrame(rows)


def _evaluate_policy(policy: pd.Series, scenario: dict) -> dict:
    """정책 한 건에 대해 매칭 통과 여부와 설명 사유를 함께 만듭니다."""

    match_reasons = []
    check_reasons = []

    employment_check = _check_text("고용 형태", policy["employment_type"], scenario["employment_type"])
    if "육아휴직급여" in str(policy["policy_name"]) and scenario.get("employment_type") in ["프리랜서", "자영업"]:
        employment_check = {
            "status": "needs_check",
            "reason": "프리랜서 또는 자영업자는 고용보험/근로자 요건 확인 필요",
        }

    checks = [
        _check_life_event(policy["life_event"], scenario),
        _check_text("지역", policy["region"], scenario["region"]),
        _check_range("나이", scenario["age"], policy["min_age"], policy["max_age"]),
        _check_text("혼인 상태", policy["marital_status"], scenario["marital_status"]),
        _check_range("자녀 수", scenario["child_count"], policy["min_child_count"], policy["max_child_count"]),
        _check_range("가구 월소득", scenario["household_income"], policy["min_income"], policy["max_income"]),
        _check_text("주거 형태", policy["housing_type"], scenario["housing_type"]),
        _check_text("주택 보유", policy["home_owner"], scenario["home_owner"]),
        employment_check,
    ]

    for check in checks:
        if check["status"] == "fail":
            return {
                "match_status": "not_matched",
                "match_reasons": match_reasons,
                "check_reasons": [check["reason"]],
            }
        if check["status"] == "needs_check":
            check_reasons.append(check["reason"])
        else:
            match_reasons.append(check["reason"])

    if str(policy["benefit_type"]).strip() == "확인필요":
        check_reasons.append("혜택 금액이 조건별로 달라 공식 사이트 확인 필요")

    child_age_check = _check_child_age_policy(policy, scenario)
    timing_check = _check_current_timing_policy(policy, scenario)
    for extra_check in [child_age_check, timing_check]:
        if extra_check["status"] == "needs_check":
            check_reasons.append(extra_check["reason"])
        elif extra_check["status"] == "pass" and extra_check["reason"]:
            match_reasons.append(extra_check["reason"])

    if check_reasons:
        status = "needs_check"
    else:
        status = "recommended"

    return {
        "match_status": status,
        "match_reasons": match_reasons,
        "check_reasons": check_reasons,
        "child_age_check": child_age_check["reason"],
        "timing_check": timing_check["reason"],
    }


def _calculate_totals(policies: pd.DataFrame) -> dict:
    """benefit_type별로 월지급, 월환산, 일회성 혜택을 분리 계산합니다."""

    if policies.empty:
        return {
            "monthly_benefit_total": 0,
            "one_time_benefit_total": 0,
            "monthly_equivalent_total": 0,
            "existing_monthly_benefit_total": 0,
            "new_monthly_benefit_total": 0,
            "after_monthly_benefit_total": 0,
            "existing_one_time_benefit_total": 0,
            "new_one_time_benefit_total": 0,
            "after_one_time_benefit_total": 0,
            "one_year_benefit_total": 0,
            "long_term_reference_total": 0,
            "total_benefit": 0,
        }

    new_eligible = policies[
        policies["match_status"].isin(["recommended", "new"])
        & policies["benefit_type"].isin(["월지급", "일회성", "월환산"])
    ].copy()
    existing_eligible = policies[
        policies["match_status"].eq("already_receiving")
        & policies["benefit_type"].isin(["월지급", "일회성", "월환산"])
    ].copy()

    monthly = new_eligible[new_eligible["benefit_type"] == "월지급"]
    monthly_equivalent = new_eligible[new_eligible["benefit_type"] == "월환산"]
    one_time = new_eligible[new_eligible["benefit_type"] == "일회성"]
    existing_monthly = existing_eligible[existing_eligible["benefit_type"].isin(["월지급", "월환산"])]
    existing_one_time = existing_eligible[existing_eligible["benefit_type"] == "일회성"]

    monthly_total = int(monthly["benefit_amount"].sum())
    monthly_equivalent_total = int(monthly_equivalent["benefit_amount"].sum())
    one_time_total = int(one_time["benefit_amount"].sum())
    new_monthly_total = monthly_total + monthly_equivalent_total
    existing_monthly_total = int(existing_monthly["benefit_amount"].sum())
    existing_one_time_total = int(existing_one_time["benefit_amount"].sum())
    after_monthly_total = existing_monthly_total + new_monthly_total
    after_one_time_total = existing_one_time_total + one_time_total

    one_year_recurring_total = (
        (monthly["benefit_amount"] * monthly["benefit_period_months"].clip(upper=12)).sum()
        + (
            monthly_equivalent["benefit_amount"]
            * monthly_equivalent["benefit_period_months"].clip(upper=12)
        ).sum()
    )
    one_year_benefit_total = int(one_year_recurring_total + one_time_total)

    long_term_reference_total = (
        (monthly["benefit_amount"] * monthly["benefit_period_months"]).sum()
        + (monthly_equivalent["benefit_amount"] * monthly_equivalent["benefit_period_months"]).sum()
        + one_time_total
    )
    long_term_reference_total = int(long_term_reference_total)

    return {
        "monthly_benefit_total": monthly_total,
        "one_time_benefit_total": one_time_total,
        "monthly_equivalent_total": monthly_equivalent_total,
        "existing_monthly_benefit_total": existing_monthly_total,
        "new_monthly_benefit_total": new_monthly_total,
        "after_monthly_benefit_total": after_monthly_total,
        "existing_one_time_benefit_total": existing_one_time_total,
        "new_one_time_benefit_total": one_time_total,
        "after_one_time_benefit_total": after_one_time_total,
        "one_year_benefit_total": one_year_benefit_total,
        "long_term_reference_total": long_term_reference_total,
        "total_benefit": one_year_benefit_total,
    }


def _build_result_frame(rows: list[dict]) -> pd.DataFrame:
    """빈 결과여도 앱이 참조하는 컬럼이 항상 존재하도록 DataFrame을 만듭니다."""

    if not rows:
        return pd.DataFrame(columns=RESULT_COLUMNS)

    frame = pd.DataFrame(rows)
    for column in RESULT_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    return frame[RESULT_COLUMNS]


def _is_included_in_yearly_total(policy) -> bool:
    return (
        policy.get("match_status") in ["recommended", "new"]
        and policy.get("benefit_type") in ["월지급", "일회성", "월환산"]
    )


def _is_included_in_existing_monthly_total(policy) -> bool:
    return policy.get("match_status") == "already_receiving" and policy.get("benefit_type") in ["월지급", "월환산"]


def _is_included_in_existing_one_time_total(policy) -> bool:
    return policy.get("match_status") == "already_receiving" and policy.get("benefit_type") == "일회성"


def _is_included_in_new_monthly_total(policy) -> bool:
    return policy.get("match_status") in ["recommended", "new"] and policy.get("benefit_type") in ["월지급", "월환산"]


def _is_included_in_new_one_time_total(policy) -> bool:
    return policy.get("match_status") in ["recommended", "new"] and policy.get("benefit_type") == "일회성"


def _check_child_age_policy(policy: pd.Series, scenario: dict) -> dict:
    """현재 상태의 양육성 월지급 정책을 자녀 나이 기준으로 보수적으로 점검합니다."""

    if scenario.get("is_future_change", True):
        return {"status": "pass", "reason": "자녀 나이: 미래 출산 직후 가정"}

    policy_name = str(policy["policy_name"])
    child_age = scenario.get("youngest_child_age") or scenario.get("child_age") or "해당 없음"

    if "부모급여" in policy_name:
        if child_age in ["0세", "1세"]:
            return {"status": "pass", "reason": f"자녀 나이: {child_age} 부모급여 후보"}
        return {
            "status": "needs_check",
            "reason": "자녀 나이에 따라 부모급여 수급 가능 여부 확인 필요",
        }

    if "아동수당" in policy_name:
        if child_age in ["0세", "1세", "2세", "3세 이상"]:
            return {"status": "pass", "reason": "아동수당은 정확한 만 나이 기준 확인 필요"}
        return {"status": "needs_check", "reason": "자녀 나이에 따라 아동수당 수급 가능 여부 확인 필요"}

    if "가정양육수당" in policy_name or "보육료" in policy_name:
        return {
            "status": "needs_check",
            "reason": "어린이집 이용 여부 등 추가 조건 확인 필요",
        }

    return {"status": "pass", "reason": ""}


def _check_current_timing_policy(policy: pd.Series, scenario: dict) -> dict:
    """현재 상태에서 이미 지나갔을 수 있는 출산 직후성 정책은 확인 후보로 둡니다."""

    if scenario.get("is_future_change", True):
        return {"status": "pass", "reason": "신청 시점: 미래 출산 직후 가정"}

    policy_name = str(policy["policy_name"])
    life_event = str(policy["life_event"])
    immediate_keywords = ["첫만남이용권", "임신출산 진료비", "산후조리", "출산지원금"]

    if life_event in ["첫째 출산", "둘째 출산"] and any(keyword in policy_name for keyword in immediate_keywords):
        return {
            "status": "needs_check",
            "reason": "현재 상태에서 이미 발생한 출산 이벤트일 수 있어 신청 가능 기간 확인 필요",
        }

    return {"status": "pass", "reason": ""}




def _check_text(label: str, policy_value: str, user_value: str) -> dict:
    """문자 조건을 검사합니다. 복수 조건은 '|'로 구분합니다."""

    policy_value = "" if pd.isna(policy_value) else str(policy_value).strip()
    user_value = "" if pd.isna(user_value) else str(user_value).strip()

    if policy_value in ANY_VALUES:
        return {"status": "pass", "reason": f"{label}: 제한 없음"}

    if policy_value == "확인필요":
        return {"status": "needs_check", "reason": f"{label}: 공식 조건 확인 필요"}

    allowed_values = {value.strip() for value in policy_value.split("|")}
    if user_value in allowed_values or "무관" in allowed_values or "전체" in allowed_values:
        return {"status": "pass", "reason": f"{label}: {user_value} 조건 충족"}

    return {"status": "fail", "reason": f"{label}: {user_value}은(는) {policy_value} 조건과 불일치"}


def _check_life_event(policy_value: str, scenario: dict) -> dict:
    """현재 단계에 이미 포함된 생애 이벤트까지 함께 고려합니다."""

    policy_value = "" if pd.isna(policy_value) else str(policy_value).strip()
    if policy_value in ANY_VALUES:
        return {"status": "pass", "reason": "생애 이벤트: 제한 없음"}

    if policy_value == "확인필요":
        return {"status": "needs_check", "reason": "생애 이벤트: 공식 조건 확인 필요"}

    allowed_policy_events = {value.strip() for value in policy_value.split("|")}
    scenario_events = scenario.get("eligible_life_events") or [scenario.get("life_event", "")]
    scenario_events = {str(value).strip() for value in scenario_events}

    if allowed_policy_events & scenario_events:
        matched_events = ", ".join(sorted(allowed_policy_events & scenario_events))
        return {"status": "pass", "reason": f"생애 이벤트: {matched_events} 조건 충족"}

    scenario_event_text = ", ".join(sorted(scenario_events))
    return {
        "status": "fail",
        "reason": f"생애 이벤트: {scenario_event_text}은(는) {policy_value} 조건과 불일치",
    }


def _check_range(label: str, value: int, minimum: int, maximum: int) -> dict:
    """숫자 범위를 검사합니다. 0은 제한 없음으로 처리합니다."""

    value = int(value or 0)
    minimum = int(minimum or 0)
    maximum = int(maximum or 0)

    if minimum and value < minimum:
        return {"status": "fail", "reason": f"{label}: {value:,}이(가) 최소 {minimum:,} 미만"}

    if maximum and value > maximum:
        return {"status": "fail", "reason": f"{label}: {value:,}이(가) 최대 {maximum:,} 초과"}

    if minimum or maximum:
        if maximum:
            return {"status": "pass", "reason": f"{label}: {minimum:,}~{maximum:,} 범위 충족"}
        return {"status": "pass", "reason": f"{label}: 최소 {minimum:,} 이상 충족"}

    return {"status": "pass", "reason": f"{label}: 제한 없음"}
