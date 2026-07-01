from pathlib import Path

import pandas as pd


ANY_VALUES = {"전체", "무관", "상관없음", "any", "ANY", ""}


def load_policies(path: str) -> pd.DataFrame:
    """CSV 정책 데이터를 읽고 숫자 컬럼을 계산 가능한 형태로 정리합니다."""

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
        policies[column] = pd.to_numeric(policies[column], errors="coerce").fillna(0).astype(int)

    return policies


def match_policies_for_scenarios(policies: pd.DataFrame, scenarios: list[dict], current_policy_names: list[str]) -> dict:
    """각 시나리오별로 정책을 규칙 기반 매칭하고 상태를 분류합니다."""

    results = {}
    current_matched_names = set()
    current_policy_names = set(current_policy_names)

    for scenario in scenarios:
        matched_rows = []

        for _, policy in policies.iterrows():
            match_result = _match_single_policy(policy, scenario)
            if match_result == "not_matched":
                continue

            policy_dict = policy.to_dict()
            policy_name = policy_dict["policy_name"]

            if policy_name in current_policy_names:
                status = "duplicate"
            elif match_result == "needs_check":
                status = "needs_check"
            elif scenario["name"] != "현재 상태" and policy_name not in current_matched_names:
                status = "new"
            else:
                status = "recommended"

            policy_dict["match_status"] = status
            matched_rows.append(policy_dict)

        matched_df = pd.DataFrame(matched_rows)

        if scenario["name"] == "현재 상태" and not matched_df.empty:
            current_matched_names = set(matched_df["policy_name"].tolist()) | current_policy_names

        results[scenario["name"]] = {"scenario": scenario, "policies": matched_df}

    return results


def calculate_benefit_summary(matched_results: dict) -> pd.DataFrame:
    """시나리오별 월 환산 혜택, 일회성 혜택, 총 예상 혜택을 계산합니다."""

    rows = []

    for scenario_name, result in matched_results.items():
        policies = result["policies"]

        if policies.empty:
            monthly_total = 0
            one_time_total = 0
            total_benefit = 0
        else:
            eligible_policies = policies[policies["match_status"] != "needs_check"].copy()
            monthly_policies = eligible_policies[eligible_policies["benefit_type"] == "월지급"]
            one_time_policies = eligible_policies[eligible_policies["benefit_type"] == "일회성"]

            monthly_total = int(monthly_policies["benefit_amount"].sum())
            one_time_total = int(one_time_policies["benefit_amount"].sum())
            period_benefit = (monthly_policies["benefit_amount"] * monthly_policies["benefit_period_months"]).sum()
            total_benefit = int(period_benefit + one_time_total)

        rows.append(
            {
                "시나리오": scenario_name,
                "정책 적용 전 기준값": 0,
                "월 환산 예상 혜택": monthly_total,
                "일회성 예상 혜택": one_time_total,
                "정책 적용 후 효과": monthly_total,
                "총 예상 혜택": total_benefit,
            }
        )

    return pd.DataFrame(rows)


def _match_single_policy(policy: pd.Series, scenario: dict) -> str:
    """정책 한 건이 시나리오 조건에 맞는지 판단합니다."""

    checks = [
        _match_text(policy["life_event"], scenario["life_event"]),
        _match_text(policy["region"], scenario["region"]),
        _match_range(scenario["age"], policy["min_age"], policy["max_age"]),
        _match_range(scenario["household_income"], policy["min_income"], policy["max_income"]),
        _match_text(policy["housing_type"], scenario["housing_type"]),
        _match_text(policy["home_owner"], scenario["home_owner"]),
        _match_text(policy["marital_status"], scenario["marital_status"]),
        _match_range(scenario["child_count"], policy["min_child_count"], policy["max_child_count"]),
    ]

    if any(check == "fail" for check in checks):
        return "not_matched"
    if any(check == "needs_check" for check in checks):
        return "needs_check"
    return "matched"


def _match_text(policy_value: str, user_value: str) -> str:
    """문자 조건을 비교합니다. '확인필요'는 결과에서 별도 상태로 표시합니다."""

    if pd.isna(policy_value) or str(policy_value).strip() in ANY_VALUES:
        return "pass"

    normalized_policy_value = str(policy_value).strip()
    if normalized_policy_value == "확인필요":
        return "needs_check"

    allowed_values = {value.strip() for value in normalized_policy_value.split("|")}
    if user_value in allowed_values:
        return "pass"

    return "fail"


def _match_range(value: int, minimum: int, maximum: int) -> str:
    """숫자 범위 조건을 비교합니다. 0은 제한 없음으로 봅니다."""

    if minimum and value < minimum:
        return "fail"
    if maximum and value > maximum:
        return "fail"
    return "pass"
