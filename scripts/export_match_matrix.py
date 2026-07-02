from audit_helpers import (
    PROJECT_ROOT,
    TEST_CASES,
    add_project_root_to_path,
    ensure_runtime_with_pandas,
    status_for_policy,
    validate_profile,
)


ensure_runtime_with_pandas()
add_project_root_to_path()

import pandas as pd

from src.policy_matcher import _evaluate_policy, calculate_benefit_summary, load_policies, match_policies_for_scenarios
from src.scenarios import build_life_event_scenarios


POLICY_PATH = PROJECT_ROOT / "data" / "policies.csv"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "match_matrix.csv"


def main() -> None:
    policies = load_policies(str(POLICY_PATH))
    rows = []

    for profile in TEST_CASES:
        scenarios = build_life_event_scenarios(profile)
        matched_results = match_policies_for_scenarios(policies, scenarios, profile["current_policies"])
        benefit_summary = calculate_benefit_summary(matched_results).set_index("시나리오")
        validation_summary = " | ".join(f"{level}: {message}" for level, message in validate_profile(profile))

        current_policy_names = set(profile["current_policies"])
        current_matched_names = set(current_policy_names)

        for scenario in scenarios:
            scenario_name = scenario["name"]
            matched_names = set(matched_results[scenario_name]["policies"]["policy_name"].tolist())

            for _, policy in policies.iterrows():
                status = status_for_policy(policy, scenario, current_policy_names, current_matched_names, _evaluate_policy)
                is_visible_in_app = policy["policy_name"] in matched_names
                visible_in_recommendation_cards = status["match_status"] in ["new", "recommended"]
                visible_in_needs_check_section = status["match_status"] == "needs_check"
                visible_in_already_receiving_section = status["match_status"] == "already_receiving"
                included_in_existing_monthly_total = status["included_in_existing_monthly_total"]
                included_in_existing_one_time_total = status["included_in_existing_one_time_total"]
                included_in_new_monthly_total = status["included_in_new_monthly_total"]
                included_in_new_one_time_total = status["included_in_new_one_time_total"]
                included_in_after_monthly_total = status["included_in_after_monthly_total"]
                included_in_after_one_time_total = status["included_in_after_one_time_total"]

                rows.append(
                    {
                        "case_id": profile["case_id"],
                        "case_label": profile["label"],
                        "input_region": profile["region"],
                        "input_marital_status": profile["marital_status"],
                        "input_child_count": profile["child_count"],
                        "input_youngest_child_age": profile.get("youngest_child_age", "해당 없음"),
                        "input_housing_type": profile["housing_type"],
                        "input_home_owner": profile["home_owner"],
                        "input_employment_type": profile["employment_type"],
                        "input_current_policies": "|".join(profile["current_policies"]),
                        "input_marriage_plan": profile["marriage_plan"],
                        "input_birth_plan": profile["birth_plan"],
                        "input_expected_child_count": profile["expected_child_count"],
                        "input_birth_timing": profile["birth_timing"],
                        "input_validation": validation_summary,
                        "scenario": scenario_name,
                        "scenario_life_events": "|".join(scenario.get("eligible_life_events", [scenario["life_event"]])),
                        "scenario_is_future_change": scenario.get("is_future_change", True),
                        "generated_by_future_plan": scenario.get("generated_by_future_plan", False),
                        "scenario_plan_note": scenario.get("plan_note", ""),
                        "scenario_youngest_child_age": scenario.get("youngest_child_age", "해당 없음"),
                        "policy_name": policy["policy_name"],
                        "policy_category": policy["category"],
                        "policy_life_event": policy["life_event"],
                        "policy_region": policy["region"],
                        "policy_marital_status": policy["marital_status"],
                        "policy_child_range": f"{policy['min_child_count']}~{policy['max_child_count']}",
                        "policy_housing_type": policy["housing_type"],
                        "policy_home_owner": policy["home_owner"],
                        "policy_employment_type": policy["employment_type"],
                        "benefit_type": policy["benefit_type"],
                        "benefit_amount": policy["benefit_amount"],
                        "benefit_period_months": policy["benefit_period_months"],
                        "match_status": status["match_status"],
                        "visible_in_app": is_visible_in_app,
                        "visible_in_recommendation_cards": visible_in_recommendation_cards,
                        "visible_in_needs_check_section": visible_in_needs_check_section,
                        "visible_in_already_receiving_section": visible_in_already_receiving_section,
                        "match_reasons": status["match_reasons"],
                        "check_or_exclude_reasons": status["check_reasons"],
                        "child_age_check": status["child_age_check"],
                        "timing_check": status["timing_check"],
                        "included_in_monthly_total": included_in_new_monthly_total,
                        "included_in_one_time_total": included_in_new_one_time_total,
                        "included_in_existing_monthly_total": included_in_existing_monthly_total,
                        "included_in_existing_one_time_total": included_in_existing_one_time_total,
                        "included_in_new_monthly_total": included_in_new_monthly_total,
                        "included_in_new_one_time_total": included_in_new_one_time_total,
                        "included_in_after_monthly_total": included_in_after_monthly_total,
                        "included_in_after_one_time_total": included_in_after_one_time_total,
                        "included_in_yearly_total": status["included_in_yearly_total"],
                        "existing_monthly_benefit_total_for_scenario": benefit_summary.loc[scenario_name, "현재 이용 중 혜택"],
                        "new_monthly_benefit_total_for_scenario": benefit_summary.loc[scenario_name, "신규 추천 월 혜택"],
                        "after_monthly_benefit_total_for_scenario": benefit_summary.loc[scenario_name, "추가 추천 반영 후"],
                        "existing_one_time_benefit_total_for_scenario": benefit_summary.loc[scenario_name, "현재 이용 중 일회성 혜택"],
                        "new_one_time_benefit_total_for_scenario": benefit_summary.loc[scenario_name, "신규 추천 일회성 혜택"],
                        "after_one_time_benefit_total_for_scenario": benefit_summary.loc[scenario_name, "추천 반영 후 일회성 혜택"],
                        "monthly_benefit_total_for_scenario": benefit_summary.loc[scenario_name, "신규 추천 월 혜택"],
                        "one_time_benefit_total_for_scenario": benefit_summary.loc[scenario_name, "신규 추천 일회성 혜택"],
                        "one_year_benefit_total_for_scenario": benefit_summary.loc[scenario_name, "1년 기준 단순 합산 지원"],
                        "needs_check_count_for_scenario": benefit_summary.loc[scenario_name, "확인 필요 정책 수"],
                        "new_policy_count_for_scenario": benefit_summary.loc[scenario_name, "신규 정책 수"],
                        "official_site": policy["official_site"],
                        "source_name": policy["source_name"],
                        "source_date": policy["source_date"],
                    }
                )

            if scenario_name == "현재 상태":
                current_matched_names |= matched_names

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    matrix = pd.DataFrame(rows)
    matrix.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

    print(f"created: {OUTPUT_PATH}")
    print(f"rows: {len(matrix)}")
    print(matrix["match_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
