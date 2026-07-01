def build_life_event_scenarios(user_profile: dict) -> list[dict]:
    """사용자 입력을 바탕으로 현재 단계에 맞는 생애변화 시나리오를 생성합니다."""

    base_household_income = user_profile["user_income"] + user_profile["partner_income"]
    current_child_count = int(user_profile["child_count"])
    current_life_events = ["현재"]

    if user_profile["marital_status"] == "기혼":
        current_life_events.append("결혼")
    if current_child_count >= 1:
        current_life_events.append("첫째 출산")
    if current_child_count >= 2:
        current_life_events.append("둘째 출산")

    current = {
        "name": "현재 상태",
        "life_event": "현재",
        "eligible_life_events": current_life_events,
        "is_future_change": False,
        "age": user_profile["age"],
        "region": user_profile["region"],
        "marital_status": user_profile["marital_status"],
        "child_count": current_child_count,
        "household_income": base_household_income,
        "housing_type": user_profile["housing_type"],
        "home_owner": user_profile["home_owner"],
        "employment_type": user_profile["employment_type"],
    }

    scenarios = [current]

    if user_profile["marital_status"] != "기혼":
        married = current.copy()
        married.update(
            {
                "name": "결혼 후",
                "life_event": "결혼",
                "eligible_life_events": ["결혼"],
                "is_future_change": True,
                "marital_status": "기혼",
            }
        )
        scenarios.append(married)

    married_base = current.copy()
    married_base.update({"marital_status": "기혼"})

    if current_child_count < 1:
        first_child = married_base.copy()
        first_child.update(
            {
                "name": "첫째 출산 후",
                "life_event": "첫째 출산",
                "eligible_life_events": ["첫째 출산"],
                "is_future_change": True,
                "child_count": 1,
                "household_income": _adjust_income_for_dual_income_plan(
                    base_household_income,
                    user_profile["partner_income"],
                    user_profile["dual_income"],
                ),
            }
        )
        scenarios.append(first_child)

    if current_child_count < 2:
        second_child = married_base.copy()
        second_child.update(
            {
                "name": "둘째 출산 후" if current_child_count == 0 else "둘째 출산 후 (다음 자녀)",
                "life_event": "둘째 출산",
                "eligible_life_events": ["둘째 출산"],
                "is_future_change": True,
                "child_count": 2,
                "household_income": _adjust_income_for_dual_income_plan(
                    base_household_income,
                    user_profile["partner_income"],
                    user_profile["dual_income"],
                ),
            }
        )
        scenarios.append(second_child)
    else:
        multi_child = current.copy()
        multi_child.update(
            {
                "name": "다자녀 상태 확인",
                "life_event": "둘째 출산",
                "eligible_life_events": ["둘째 출산"],
                "is_future_change": False,
                "child_count": current_child_count,
            }
        )
        scenarios.append(multi_child)

    return scenarios


def _adjust_income_for_dual_income_plan(household_income: int, partner_income: int, dual_income: str) -> int:
    """출산 후 맞벌이 유지 여부에 따라 가구소득을 단순 조정합니다."""

    if dual_income == "일시 중단":
        return household_income - int(partner_income * 0.5)
    if dual_income == "미정":
        return household_income - int(partner_income * 0.25)
    return household_income
