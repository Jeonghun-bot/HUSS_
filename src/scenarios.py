NEAR_TERM_MARRIAGE_PLANS = {"1년 내", "1년 이내", "2년 내", "2년 이내"}


def build_life_event_scenarios(user_profile: dict) -> list[dict]:
    """사용자 현재 상태와 미래 계획을 바탕으로 필요한 시나리오만 생성합니다."""

    base_household_income = user_profile["user_income"] + user_profile["partner_income"]
    current_child_count = int(user_profile["child_count"])
    expected_child_count = int(user_profile.get("expected_child_count", current_child_count) or 0)
    marriage_plan = user_profile.get("marriage_plan", "없음")
    birth_plan = user_profile.get("birth_plan", "없음")
    birth_timing = user_profile.get("birth_timing", "미정")
    youngest_child_age = user_profile.get("youngest_child_age") or user_profile.get("child_age") or "해당 없음"

    current = _build_base_current_scenario(
        user_profile=user_profile,
        household_income=base_household_income,
        current_child_count=current_child_count,
        youngest_child_age=youngest_child_age,
    )

    scenarios = [current]

    if user_profile["marital_status"] == "미혼" and marriage_plan in NEAR_TERM_MARRIAGE_PLANS:
        married = current.copy()
        married.update(
            {
                "name": "결혼 후",
                "life_event": "결혼",
                "eligible_life_events": ["결혼"],
                "is_future_change": True,
                "generated_by_future_plan": True,
                "marital_status": "기혼",
                "plan_note": f"사용자가 선택한 결혼 계획 {marriage_plan}를 기준으로 한 정책 후보입니다.",
            }
        )
        scenarios.append(married)

    if birth_plan != "없음" and expected_child_count > current_child_count:
        target_child_count = expected_child_count
        for next_child_count in range(current_child_count + 1, target_child_count + 1):
            scenarios.append(
                _build_birth_scenario(
                    current=current,
                    user_profile=user_profile,
                    base_household_income=base_household_income,
                    next_child_count=next_child_count,
                    birth_timing=birth_timing,
                )
            )

    return scenarios


def _build_base_current_scenario(
    *,
    user_profile: dict,
    household_income: int,
    current_child_count: int,
    youngest_child_age: str,
) -> dict:
    current_life_events = ["현재"]

    if user_profile["marital_status"] == "기혼":
        current_life_events.append("결혼")
    if current_child_count >= 1:
        current_life_events.append("첫째 출산")
    if current_child_count >= 2:
        current_life_events.append("둘째 출산")

    return {
        "name": "현재 상태",
        "life_event": "현재",
        "eligible_life_events": current_life_events,
        "is_future_change": False,
        "generated_by_future_plan": False,
        "plan_note": "현재 입력 조건을 기준으로 한 정책 후보입니다.",
        "age": user_profile["age"],
        "region": user_profile["region"],
        "marital_status": user_profile["marital_status"],
        "child_count": current_child_count,
        "youngest_child_age": youngest_child_age if current_child_count > 0 else "해당 없음",
        "child_age": youngest_child_age if current_child_count > 0 else "해당 없음",
        "household_income": household_income,
        "housing_type": user_profile["housing_type"],
        "home_owner": user_profile["home_owner"],
        "employment_type": user_profile["employment_type"],
    }


def _build_birth_scenario(
    *,
    current: dict,
    user_profile: dict,
    base_household_income: int,
    next_child_count: int,
    birth_timing: str,
) -> dict:
    if next_child_count == 1:
        name = "첫째 출산 후"
        life_event = "첫째 출산"
    elif next_child_count == 2:
        name = "둘째 출산 후" if current["child_count"] == 0 else "둘째 출산 후 (다음 자녀)"
        life_event = "둘째 출산"
    else:
        name = "추가 자녀 출산 후"
        life_event = "둘째 출산"

    scenario = current.copy()
    scenario.update(
        {
            "name": name,
            "life_event": life_event,
            "eligible_life_events": [life_event],
            "is_future_change": True,
            "generated_by_future_plan": True,
            "marital_status": "기혼",
            "child_count": next_child_count,
            "youngest_child_age": "0세",
            "child_age": "0세",
            "household_income": _adjust_income_for_dual_income_plan(
                base_household_income,
                user_profile["partner_income"],
                user_profile["dual_income"],
            ),
            "plan_note": (
                f"{name}: 사용자가 선택한 출산 예정 시점 {birth_timing}을 기준으로 한 정책 후보입니다. "
                "미래 정책 변경 가능성은 반영하지 않습니다."
            ),
        }
    )
    return scenario


def _adjust_income_for_dual_income_plan(household_income: int, partner_income: int, dual_income: str) -> int:
    """출산 후 맞벌이 유지 여부에 따라 가구소득을 단순 조정합니다."""

    if dual_income == "일시 중단":
        return household_income - int(partner_income * 0.5)
    if dual_income == "미정":
        return household_income - int(partner_income * 0.25)
    return household_income
