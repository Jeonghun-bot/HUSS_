from audit_helpers import (
    PROJECT_ROOT,
    TEST_CASES,
    add_project_root_to_path,
    ensure_runtime_with_pandas,
    expected_scenario_names,
    status_for_policy,
    validate_profile,
)


ensure_runtime_with_pandas()
add_project_root_to_path()

import pandas as pd

from src.policy_matcher import _evaluate_policy, calculate_benefit_summary, load_policies, match_policies_for_scenarios
from src.scenarios import build_life_event_scenarios


POLICY_PATH = PROJECT_ROOT / "data" / "policies.csv"


def main() -> None:
    policies = load_policies(str(POLICY_PATH))
    print_policy_condition_table(policies)

    data_quality_issues = check_policy_data_quality(policies)
    print_section("데이터 품질 점검")
    print_issues(data_quality_issues)

    all_case_issues = []
    for profile in TEST_CASES:
        issues = run_case(profile, policies)
        all_case_issues.extend([(profile["case_id"], *issue) for issue in issues])

    print_section("전체 요약")
    fail_count = sum(1 for _, level, _ in all_case_issues + [("DATA", *i) for i in data_quality_issues] if level == "FAIL")
    warning_count = sum(1 for _, level, _ in all_case_issues + [("DATA", *i) for i in data_quality_issues] if level == "WARNING")

    if fail_count:
        print(f"FAIL {fail_count}개, WARNING {warning_count}개가 발견되었습니다.")
    elif warning_count:
        print(f"PASS with WARNING: 치명적 실패는 없고 WARNING {warning_count}개가 있습니다.")
    else:
        print("PASS: 핵심 정책 추천 로직 점검을 통과했습니다.")


def print_policy_condition_table(policies: pd.DataFrame) -> None:
    print_section("정책별 조건표")
    columns = [
        "policy_name",
        "life_event",
        "region",
        "marital_status",
        "min_child_count",
        "max_child_count",
        "housing_type",
        "home_owner",
        "employment_type",
        "benefit_type",
        "benefit_amount",
        "benefit_period_months",
    ]
    print(policies[columns].to_string(index=False))


def check_policy_data_quality(policies: pd.DataFrame) -> list[tuple[str, str]]:
    issues = []
    required_columns = [
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
    ]

    missing_columns = [column for column in required_columns if column not in policies.columns]
    if missing_columns:
        issues.append(("FAIL", f"필수 컬럼 누락: {', '.join(missing_columns)}"))

    duplicate_names = policies[policies["policy_name"].duplicated()]["policy_name"].tolist()
    if duplicate_names:
        issues.append(("WARNING", f"중복 정책명 존재: {', '.join(duplicate_names)}"))

    for _, policy in policies.iterrows():
        name = policy["policy_name"]
        if not str(policy["official_site"]).startswith("http"):
            issues.append(("FAIL", f"{name}: official_site가 URL 형식이 아닙니다."))
        if not str(policy["source_name"]).strip():
            issues.append(("FAIL", f"{name}: source_name이 비어 있습니다."))
        if not str(policy["source_date"]).strip():
            issues.append(("FAIL", f"{name}: source_date가 비어 있습니다."))
        if policy["benefit_type"] == "확인필요" and int(policy["benefit_amount"]) != 0:
            issues.append(("WARNING", f"{name}: 확인필요 정책인데 benefit_amount가 0이 아닙니다."))
        if policy["benefit_type"] != "확인필요" and int(policy["benefit_amount"]) < 0:
            issues.append(("FAIL", f"{name}: benefit_amount가 음수입니다."))
        if int(policy["max_child_count"]) and int(policy["min_child_count"]) > int(policy["max_child_count"]):
            issues.append(("FAIL", f"{name}: 자녀 수 min/max가 역전되었습니다."))
        if int(policy["max_age"]) and int(policy["min_age"]) > int(policy["max_age"]):
            issues.append(("FAIL", f"{name}: 나이 min/max가 역전되었습니다."))

    if not issues:
        issues.append(("PASS", "정책 CSV 필수 품질 점검 통과"))
    return issues


def run_case(profile: dict, policies: pd.DataFrame) -> list[tuple[str, str]]:
    print_section(f"케이스 {profile['case_id']} - {profile['label']}")
    issues = []

    validation_issues = validate_profile(profile)
    print("입력 유효성:")
    print_issues(validation_issues or [("PASS", "입력 조합에 치명적 충돌 없음")])
    issues.extend(validation_issues)

    scenarios = build_life_event_scenarios(profile)
    actual_names = [scenario["name"] for scenario in scenarios]
    expected_names = expected_scenario_names(profile)

    if actual_names == expected_names:
        print(f"PASS 시나리오 생성: {actual_names}")
    else:
        message = f"시나리오 불일치. expected={expected_names}, actual={actual_names}"
        print(f"FAIL {message}")
        issues.append(("FAIL", message))

    matched_results = match_policies_for_scenarios(policies, scenarios, profile["current_policies"])
    summary = calculate_benefit_summary(matched_results)
    print("\n혜택 합계:")
    print(
        summary[
            [
                "시나리오",
                "예상 월 지원 효과",
                "초기 일회성 지원",
                "1년 기준 단순 합산 지원",
                "참고용 장기 누적액",
                "확인 필요 정책 수",
                "신규 정책 수",
            ]
        ].to_string(index=False)
    )

    issues.extend(check_case_invariants(profile, policies, scenarios, matched_results))

    print("\n시나리오별 추천/확인/이미이용:")
    for scenario_name, result in matched_results.items():
        policies_df = result["policies"]
        counts = policies_df["match_status"].value_counts().to_dict() if not policies_df.empty else {}
        print(f"- {scenario_name}: {counts}")
        if not policies_df.empty:
            show = policies_df[["policy_name", "match_status", "benefit_type", "benefit_amount", "check_reasons"]]
            print(show.to_string(index=False, max_colwidth=70))

    print("\n제외 정책 예시:")
    for row in excluded_policy_rows(profile, policies, scenarios)[:10]:
        print(f"- [{row['scenario']}] {row['policy_name']}: {row['reason']}")

    print("\n케이스 판정:")
    case_issues = issues
    case_fails = [message for level, message in case_issues if level == "FAIL"]
    case_warnings = [message for level, message in case_issues if level == "WARNING"]
    if case_fails:
        print(f"FAIL: {len(case_fails)}개 실패")
    elif case_warnings:
        print(f"WARNING: {len(case_warnings)}개 경고")
    else:
        print("PASS")

    return issues


def check_case_invariants(profile: dict, policies: pd.DataFrame, scenarios: list[dict], matched_results: dict) -> list[tuple[str, str]]:
    issues = []
    scenario_names = [scenario["name"] for scenario in scenarios]

    if profile["marital_status"] == "기혼" and "결혼 후" in scenario_names:
        issues.append(("FAIL", "기혼 사용자에게 결혼 후가 미래 시나리오로 생성되었습니다."))
    if profile["child_count"] >= 1 and "첫째 출산 후" in scenario_names:
        issues.append(("FAIL", "자녀 1명 이상 사용자에게 첫째 출산 후가 미래 시나리오로 생성되었습니다."))

    current_policy_names = set(profile["current_policies"])
    for scenario_name, result in matched_results.items():
        df = result["policies"]
        if df.empty:
            continue

        already = set(df[df["match_status"] == "already_receiving"]["policy_name"].tolist())
        missing_already = current_policy_names & set(df["policy_name"].tolist()) - already
        if missing_already:
            issues.append(("FAIL", f"{scenario_name}: 현재 받고 있는 정책이 already_receiving으로 표시되지 않음: {missing_already}"))

        new_and_already = df[df["match_status"].eq("new") & df["policy_name"].isin(current_policy_names)]
        if not new_and_already.empty:
            issues.append(("FAIL", f"{scenario_name}: already_receiving 정책이 new로 분류됨"))

        needs_check_with_amount = df[df["match_status"].eq("needs_check") & df["benefit_type"].eq("확인필요")]
        if int(needs_check_with_amount["benefit_amount"].sum()) != 0:
            issues.append(("FAIL", f"{scenario_name}: 확인필요 정책 금액이 0이 아님"))

        local_regions = set(df[~df["region"].isin(["전체", profile["region"]])]["region"].tolist())
        if local_regions:
            issues.append(("FAIL", f"{scenario_name}: 다른 지역 정책 추천됨: {local_regions}"))

        if profile["home_owner"] != "무주택":
            no_home_policies = df[df["home_owner"].eq("무주택")]
            if not no_home_policies.empty:
                issues.append(("FAIL", f"{scenario_name}: 무주택 조건 정책이 {profile['home_owner']} 사용자에게 추천됨"))

    if not issues:
        issues.append(("PASS", "핵심 불변조건 통과"))
    return issues


def excluded_policy_rows(profile: dict, policies: pd.DataFrame, scenarios: list[dict]) -> list[dict]:
    rows = []
    current_policy_names = set(profile["current_policies"])
    current_matched_names = set(current_policy_names)

    for scenario in scenarios:
        for _, policy in policies.iterrows():
            status = status_for_policy(policy, scenario, current_policy_names, current_matched_names, _evaluate_policy)
            if status["match_status"] == "not_matched":
                rows.append(
                    {
                        "scenario": scenario["name"],
                        "policy_name": policy["policy_name"],
                        "reason": status["check_reasons"],
                    }
                )
    return rows


def print_section(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def print_issues(issues: list[tuple[str, str]]) -> None:
    for level, message in issues:
        print(f"{level}: {message}")


if __name__ == "__main__":
    main()
