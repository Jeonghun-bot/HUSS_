CHILD_RELATED_POLICY_KEYWORDS = [
    "부모급여",
    "아동수당",
    "보육료",
    "양육수당",
    "첫만남이용권",
    "산후조리",
    "출산",
    "아이돌봄",
]


def validate_user_profile(user_profile: dict) -> list[dict]:
    """사용자 입력 조합이 정책 해석에 영향을 줄 수 있는지 점검합니다."""

    warnings = []
    housing_type = user_profile.get("housing_type")
    home_owner = user_profile.get("home_owner")
    marital_status = user_profile.get("marital_status")
    partner_income = int(user_profile.get("partner_income", 0) or 0)
    child_count = int(user_profile.get("child_count", 0) or 0)
    expected_child_count = int(user_profile.get("expected_child_count", child_count) or 0)
    birth_plan = user_profile.get("birth_plan", "없음")
    current_policies = user_profile.get("current_policies", [])

    if housing_type == "자가" and home_owner == "무주택":
        warnings.append(
            {
                "level": "error",
                "message": "자가 거주로 입력했지만 주택 보유 여부가 무주택입니다. 입력값을 다시 확인해 주세요.",
            }
        )

    if housing_type == "월세" and home_owner == "1주택":
        warnings.append(
            {
                "level": "warning",
                "message": "월세 거주와 1주택 보유는 동시에 가능하지만, 무주택 조건 주거지원 정책에서는 제외될 수 있습니다.",
            }
        )

    if marital_status == "미혼" and partner_income > 0:
        warnings.append(
            {
                "level": "warning",
                "message": "미혼 상태에서 입력한 배우자 또는 예상 배우자 소득은 결혼 후 시나리오 계산에만 참고됩니다.",
            }
        )

    if child_count == 0 and _has_child_related_policy(current_policies):
        warnings.append(
            {
                "level": "warning",
                "message": "자녀 수가 0명인데 자녀 관련 정책을 현재 이용 중으로 선택했습니다. 입력값을 확인해 주세요.",
            }
        )

    if birth_plan != "없음" and expected_child_count <= child_count:
        warnings.append(
            {
                "level": "warning",
                "message": "예상 자녀 수가 현재 자녀 수보다 크지 않아 추가 출산 시나리오를 생성하지 않았습니다.",
            }
        )

    if child_count >= 1 and birth_plan == "첫째":
        warnings.append(
            {
                "level": "warning",
                "message": "이미 첫째 자녀가 있는 상태입니다. 둘째 출산 계획으로 해석할지 확인해 주세요.",
            }
        )

    if child_count == 0 and birth_plan in ["둘째", "추가 자녀"]:
        warnings.append(
            {
                "level": "warning",
                "message": "현재 자녀 수가 0명인데 둘째 또는 추가 자녀 출산 계획을 선택했습니다. 예상 자녀 수와 계획을 확인해 주세요.",
            }
        )

    if child_count == 1 and birth_plan == "추가 자녀":
        warnings.append(
            {
                "level": "warning",
                "message": "현재 자녀 수가 1명입니다. 추가 자녀 계획은 둘째 출산 계획으로 해석될 수 있습니다.",
            }
        )

    return warnings


def _has_child_related_policy(policy_names: list[str]) -> bool:
    for policy_name in policy_names:
        if any(keyword in policy_name for keyword in CHILD_RELATED_POLICY_KEYWORDS):
            return True
    return False
