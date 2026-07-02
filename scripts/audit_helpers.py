import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def ensure_runtime_with_pandas() -> None:
    """Allow `python3 scripts/...` even when pandas is installed on `python` only."""

    if os.environ.get("LIFEPATH_RUNTIME_REEXEC") == "1":
        return

    try:
        import pandas  # noqa: F401
    except ModuleNotFoundError:
        python_bin = "python"
        env = os.environ.copy()
        env["LIFEPATH_RUNTIME_REEXEC"] = "1"
        os.execvpe(python_bin, [python_bin, *sys.argv], env)


def add_project_root_to_path() -> None:
    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)


def make_profile(
    *,
    case_id: str,
    label: str,
    age: int,
    region: str,
    marital_status: str,
    child_count: int,
    housing_type: str,
    home_owner: str,
    employment_type: str,
    youngest_child_age: str = "해당 없음",
    current_policies: list[str] | None = None,
    user_income: int = 3000000,
    partner_income: int = 2800000,
    marriage_plan: str | None = None,
    birth_plan: str = "없음",
    expected_child_count: int | None = None,
    birth_timing: str = "미정",
) -> dict:
    if marriage_plan is None:
        marriage_plan = "1년 내" if marital_status == "미혼" else "없음"
    if expected_child_count is None:
        expected_child_count = child_count

    return {
        "case_id": case_id,
        "label": label,
        "age": age,
        "region": region,
        "marital_status": marital_status,
        "child_count": child_count,
        "youngest_child_age": youngest_child_age if child_count > 0 else "해당 없음",
        "child_age": youngest_child_age if child_count > 0 else "해당 없음",
        "user_income": user_income,
        "partner_income": partner_income,
        "housing_type": housing_type,
        "home_owner": home_owner,
        "employment_type": employment_type,
        "current_policies": current_policies or [],
        "marriage_plan": marriage_plan,
        "birth_plan": birth_plan,
        "expected_child_count": expected_child_count,
        "birth_timing": birth_timing,
        "dual_income": "유지",
    }


TEST_CASES = [
    make_profile(
        case_id="A",
        label="서울 미혼 자녀0 결혼계획없음 출산계획없음",
        age=30,
        region="서울",
        marital_status="미혼",
        child_count=0,
        housing_type="월세",
        home_owner="무주택",
        employment_type="정규직",
        marriage_plan="없음",
        birth_plan="없음",
        expected_child_count=0,
    ),
    make_profile(
        case_id="B",
        label="서울 미혼 자녀0 결혼1년내 출산계획없음",
        age=30,
        region="서울",
        marital_status="미혼",
        child_count=0,
        housing_type="월세",
        home_owner="무주택",
        employment_type="정규직",
        marriage_plan="1년 내",
        birth_plan="없음",
        expected_child_count=0,
    ),
    make_profile(
        case_id="C",
        label="서울 미혼 자녀0 결혼1년내 첫째계획",
        age=30,
        region="서울",
        marital_status="미혼",
        child_count=0,
        housing_type="월세",
        home_owner="무주택",
        employment_type="정규직",
        marriage_plan="1년 내",
        birth_plan="첫째",
        expected_child_count=1,
        birth_timing="2년 뒤",
    ),
    make_profile(
        case_id="D",
        label="부산 기혼 자녀0 첫째계획",
        age=32,
        region="부산",
        marital_status="기혼",
        child_count=0,
        housing_type="전세",
        home_owner="무주택",
        employment_type="정규직",
        birth_plan="첫째",
        expected_child_count=1,
        birth_timing="1년 내",
    ),
    make_profile(
        case_id="E",
        label="서울 기혼 자녀1 둘째계획 현재정책",
        age=30,
        region="서울",
        marital_status="기혼",
        child_count=1,
        youngest_child_age="0세",
        housing_type="월세",
        home_owner="무주택",
        employment_type="정규직",
        current_policies=["부모급여", "아동수당"],
        birth_plan="둘째",
        expected_child_count=2,
        birth_timing="2년 뒤",
    ),
    make_profile(
        case_id="F",
        label="서울 기혼 자녀1 출산계획없음",
        age=30,
        region="서울",
        marital_status="기혼",
        child_count=1,
        youngest_child_age="2세",
        housing_type="월세",
        home_owner="무주택",
        employment_type="정규직",
        birth_plan="없음",
        expected_child_count=1,
    ),
    make_profile(
        case_id="G",
        label="서울 기혼 자녀1 첫째계획 경고",
        age=30,
        region="서울",
        marital_status="기혼",
        child_count=1,
        youngest_child_age="2세",
        housing_type="월세",
        home_owner="무주택",
        employment_type="정규직",
        birth_plan="첫째",
        expected_child_count=1,
    ),
    make_profile(
        case_id="H",
        label="서울 기혼 자녀1 월세 1주택 둘째계획",
        age=30,
        region="서울",
        marital_status="기혼",
        child_count=1,
        youngest_child_age="1세",
        housing_type="월세",
        home_owner="1주택",
        employment_type="정규직",
        birth_plan="둘째",
        expected_child_count=2,
        birth_timing="2년 뒤",
    ),
    make_profile(
        case_id="I",
        label="서울 기혼 자녀1 첫만남이용권 이미이용",
        age=30,
        region="서울",
        marital_status="기혼",
        child_count=1,
        youngest_child_age="0세",
        housing_type="월세",
        home_owner="무주택",
        employment_type="정규직",
        current_policies=["첫만남이용권 첫째아"],
        birth_plan="없음",
        expected_child_count=1,
    ),
    make_profile(
        case_id="J",
        label="서울 기혼 자녀0 확인필요 정책 이미이용",
        age=35,
        region="서울",
        marital_status="기혼",
        child_count=0,
        housing_type="전세",
        home_owner="무주택",
        employment_type="정규직",
        current_policies=["서울시 신혼부부 임차보증금 이자지원"],
        birth_plan="없음",
        expected_child_count=0,
    ),
]


def validate_profile(profile: dict) -> list[tuple[str, str]]:
    """Return validation issues as (level, message)."""

    issues = []

    if profile["housing_type"] == "자가" and profile["home_owner"] == "무주택":
        issues.append(("FAIL", "자가 거주로 입력했지만 주택 보유 여부가 무주택입니다. 입력값을 다시 확인해 주세요."))

    if profile["housing_type"] == "월세" and profile["home_owner"] == "1주택":
        issues.append(("WARNING", "월세 거주와 1주택 보유는 동시에 가능하지만, 무주택 조건 주거지원 정책에서는 제외될 수 있습니다."))

    if profile["marital_status"] == "미혼" and profile["child_count"] > 0:
        issues.append(("WARNING", "미혼이면서 현재 자녀가 있는 경우 한부모/양육 정책 조건을 별도로 확인해야 합니다."))

    if profile["expected_child_count"] < profile["child_count"]:
        issues.append(("FAIL", "예상 자녀 수가 현재 자녀 수보다 작습니다."))

    if profile["partner_income"] > 0 and profile["marital_status"] == "미혼":
        issues.append(("WARNING", "미혼 상태에서 입력한 배우자 또는 예상 배우자 소득은 결혼 후 시나리오 계산에만 참고됩니다."))

    if profile["child_count"] == 0 and _has_child_related_policy(profile.get("current_policies", [])):
        issues.append(("WARNING", "자녀 수가 0명인데 자녀 관련 정책을 현재 이용 중으로 선택했습니다. 입력값을 확인해 주세요."))

    if profile["birth_plan"] != "없음" and profile["expected_child_count"] <= profile["child_count"]:
        issues.append(("WARNING", "예상 자녀 수가 현재 자녀 수보다 크지 않아 추가 출산 시나리오를 생성하지 않았습니다."))

    if profile["child_count"] >= 1 and profile["birth_plan"] == "첫째":
        issues.append(("WARNING", "이미 첫째 자녀가 있는 상태입니다. 둘째 출산 계획으로 해석할지 확인해 주세요."))

    return issues


def _has_child_related_policy(policy_names: list[str]) -> bool:
    keywords = ["부모급여", "아동수당", "보육료", "양육수당", "첫만남이용권", "산후조리", "출산", "아이돌봄"]
    return any(any(keyword in policy_name for keyword in keywords) for policy_name in policy_names)


def expected_scenario_names(profile: dict) -> list[str]:
    names = ["현재 상태"]
    if profile["marital_status"] == "미혼" and profile["marriage_plan"] in ["1년 내", "1년 이내", "2년 내", "2년 이내"]:
        names.append("결혼 후")
    if profile["birth_plan"] != "없음" and profile["expected_child_count"] > profile["child_count"]:
        for next_child_count in range(profile["child_count"] + 1, profile["expected_child_count"] + 1):
            if next_child_count == 1:
                names.append("첫째 출산 후")
            elif next_child_count == 2:
                names.append("둘째 출산 후" if profile["child_count"] == 0 else "둘째 출산 후 (다음 자녀)")
            else:
                names.append("추가 자녀 출산 후")
    return names


def status_for_policy(policy, scenario: dict, current_policy_names: set[str], current_matched_names: set[str], evaluate_policy) -> dict:
    evaluation = evaluate_policy(policy, scenario)
    policy_name = policy["policy_name"]

    if evaluation["match_status"] == "not_matched":
        status = "not_matched"
    elif policy_name in current_policy_names:
        status = "already_receiving"
    elif evaluation["match_status"] == "needs_check":
        status = "needs_check"
    elif scenario.get("is_future_change", True) and policy_name not in current_matched_names:
        status = "new"
    else:
        status = "recommended"

    included_in_existing_monthly_total = status == "already_receiving" and policy["benefit_type"] in ["월지급", "월환산"]
    included_in_existing_one_time_total = status == "already_receiving" and policy["benefit_type"] == "일회성"
    included_in_new_monthly_total = status in ["recommended", "new"] and policy["benefit_type"] in ["월지급", "월환산"]
    included_in_new_one_time_total = status in ["recommended", "new"] and policy["benefit_type"] == "일회성"

    return {
        "match_status": status,
        "match_reasons": "; ".join(evaluation["match_reasons"]),
        "check_reasons": "; ".join(evaluation["check_reasons"]),
        "child_age_check": evaluation.get("child_age_check", ""),
        "timing_check": evaluation.get("timing_check", ""),
        "included_in_yearly_total": status in ["recommended", "new"] and policy["benefit_type"] in ["월지급", "일회성", "월환산"],
        "included_in_existing_monthly_total": included_in_existing_monthly_total,
        "included_in_existing_one_time_total": included_in_existing_one_time_total,
        "included_in_new_monthly_total": included_in_new_monthly_total,
        "included_in_new_one_time_total": included_in_new_one_time_total,
        "included_in_after_monthly_total": included_in_existing_monthly_total or included_in_new_monthly_total,
        "included_in_after_one_time_total": included_in_existing_one_time_total or included_in_new_one_time_total,
    }
