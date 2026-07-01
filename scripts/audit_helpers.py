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
    current_policies: list[str] | None = None,
    user_income: int = 3000000,
    partner_income: int = 2800000,
) -> dict:
    return {
        "case_id": case_id,
        "label": label,
        "age": age,
        "region": region,
        "marital_status": marital_status,
        "child_count": child_count,
        "user_income": user_income,
        "partner_income": partner_income,
        "housing_type": housing_type,
        "home_owner": home_owner,
        "employment_type": employment_type,
        "current_policies": current_policies or [],
        "marriage_plan": "1년 이내" if marital_status == "미혼" else "없음",
        "birth_plan": "2년 이내",
        "expected_child_count": max(child_count + 1, 2),
        "birth_timing": "2년 이내",
        "dual_income": "유지",
    }


TEST_CASES = [
    make_profile(
        case_id="A",
        label="서울 미혼 자녀0 월세 무주택 정규직",
        age=30,
        region="서울",
        marital_status="미혼",
        child_count=0,
        housing_type="월세",
        home_owner="무주택",
        employment_type="정규직",
    ),
    make_profile(
        case_id="B",
        label="서울 기혼 자녀0 전세 무주택 정규직",
        age=30,
        region="서울",
        marital_status="기혼",
        child_count=0,
        housing_type="전세",
        home_owner="무주택",
        employment_type="정규직",
    ),
    make_profile(
        case_id="C",
        label="서울 기혼 자녀1 월세 무주택 정규직",
        age=30,
        region="서울",
        marital_status="기혼",
        child_count=1,
        housing_type="월세",
        home_owner="무주택",
        employment_type="정규직",
    ),
    make_profile(
        case_id="D",
        label="부산 기혼 자녀2 전세 무주택 정규직",
        age=32,
        region="부산",
        marital_status="기혼",
        child_count=2,
        housing_type="전세",
        home_owner="무주택",
        employment_type="정규직",
    ),
    make_profile(
        case_id="E",
        label="서울 기혼 자녀1 월세 무주택 정규직 현재정책",
        age=30,
        region="서울",
        marital_status="기혼",
        child_count=1,
        housing_type="월세",
        home_owner="무주택",
        employment_type="정규직",
        current_policies=["부모급여", "아동수당"],
    ),
    make_profile(
        case_id="F",
        label="경기 미혼 자녀0 월세 무주택 프리랜서",
        age=29,
        region="경기",
        marital_status="미혼",
        child_count=0,
        housing_type="월세",
        home_owner="무주택",
        employment_type="프리랜서",
    ),
    make_profile(
        case_id="G",
        label="서울 기혼 자녀0 자가 1주택 정규직",
        age=35,
        region="서울",
        marital_status="기혼",
        child_count=0,
        housing_type="자가",
        home_owner="1주택",
        employment_type="정규직",
    ),
    make_profile(
        case_id="H",
        label="서울 기혼 자녀1 월세 1주택 정규직",
        age=30,
        region="서울",
        marital_status="기혼",
        child_count=1,
        housing_type="월세",
        home_owner="1주택",
        employment_type="정규직",
    ),
]


def validate_profile(profile: dict) -> list[tuple[str, str]]:
    """Return validation issues as (level, message)."""

    issues = []

    if profile["housing_type"] == "자가" and profile["home_owner"] == "무주택":
        issues.append(("FAIL", "자가 주거 형태인데 주택 보유 여부가 무주택입니다. 입력 조합이 논리적으로 충돌합니다."))

    if profile["housing_type"] in ["월세", "전세"] and profile["home_owner"] == "1주택":
        issues.append(("WARNING", f"{profile['housing_type']} 거주와 1주택 보유는 가능하지만 주거지원 정책은 대체로 무주택 조건을 확인해야 합니다."))

    if profile["marital_status"] == "미혼" and profile["child_count"] > 0:
        issues.append(("WARNING", "미혼이면서 현재 자녀가 있는 경우 한부모/양육 정책 조건을 별도로 확인해야 합니다."))

    if profile["expected_child_count"] < profile["child_count"]:
        issues.append(("FAIL", "예상 자녀 수가 현재 자녀 수보다 작습니다."))

    if profile["partner_income"] > 0 and profile["marital_status"] == "미혼":
        issues.append(("WARNING", "미혼 상태에서 예상 배우자 소득을 입력했습니다. 결혼 후 시나리오에는 유효하지만 현재 상태 해석은 주의가 필요합니다."))

    return issues


def expected_scenario_names(profile: dict) -> list[str]:
    if profile["marital_status"] == "미혼" and profile["child_count"] == 0:
        return ["현재 상태", "결혼 후", "첫째 출산 후", "둘째 출산 후"]
    if profile["marital_status"] == "기혼" and profile["child_count"] == 0:
        return ["현재 상태", "첫째 출산 후", "둘째 출산 후"]
    if profile["marital_status"] == "기혼" and profile["child_count"] == 1:
        return ["현재 상태", "둘째 출산 후 (다음 자녀)"]
    if profile["marital_status"] == "기혼" and profile["child_count"] >= 2:
        return ["현재 상태", "다자녀 상태 확인"]
    return []


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

    return {
        "match_status": status,
        "match_reasons": "; ".join(evaluation["match_reasons"]),
        "check_reasons": "; ".join(evaluation["check_reasons"]),
    }
