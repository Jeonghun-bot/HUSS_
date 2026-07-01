def build_life_event_scenarios(user_profile: dict) -> list[dict]:
    """사용자 입력을 바탕으로 생애변화 시나리오를 자동 생성합니다."""

    base_household_income = user_profile["user_income"] + user_profile["partner_income"]

    current = {
        "name": "현재 상태",
        "life_event": "현재",
        "age": user_profile["age"],
        "region": user_profile["region"],
        "marital_status": user_profile["marital_status"],
        "child_count": user_profile["child_count"],
        "household_income": base_household_income,
        "housing_type": user_profile["housing_type"],
        "home_owner": user_profile["home_owner"],
        "employment_type": user_profile["employment_type"],
    }

    married = current.copy()
    married.update({"name": "결혼 후", "life_event": "결혼", "marital_status": "기혼"})

    first_child = married.copy()
    first_child.update(
        {
            "name": "첫째 출산 후",
            "life_event": "첫째 출산",
            "child_count": max(user_profile["child_count"], 1),
            "household_income": _adjust_income_for_dual_income_plan(
                base_household_income,
                user_profile["partner_income"],
                user_profile["dual_income"],
            ),
        }
    )

    second_child = first_child.copy()
    second_child.update({"name": "둘째 출산 후", "life_event": "둘째 출산", "child_count": max(user_profile["child_count"], 2)})

    # MVP에서는 사용자의 계획 여부와 관계없이 4개 시나리오를 모두 보여줍니다.
    # 그래야 현재 조건 대비 결혼/출산 이후 정책 수혜 가능성을 한 화면에서 비교할 수 있습니다.
    return [current, married, first_child, second_child]


def _adjust_income_for_dual_income_plan(household_income: int, partner_income: int, dual_income: str) -> int:
    """출산 후 맞벌이 유지 여부에 따라 가구소득을 단순 조정합니다."""

    if dual_income == "일시 중단":
        return household_income - int(partner_income * 0.5)
    if dual_income == "미정":
        return household_income - int(partner_income * 0.25)
    return household_income
