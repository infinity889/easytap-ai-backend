from __future__ import annotations

from .models import Profile, Skill, Vacancy


def _normalize(values: list[str]) -> set[str]:
    return {value.strip().lower() for value in values if value.strip()}


KAZAKHSTAN_LOCATION_KEYWORDS = {
    "kazakhstan",
    "қазақстан",
    "казахстан",
    "atyrau",
    "атырау",
    "almaty",
    "алматы",
    "astana",
    "nur-sultan",
    "нур-султан",
    "shymkent",
    "шымкент",
    "aktau",
    "актау",
    "karaganda",
    "караганда",
    "kostanay",
    "костанай",
    "pavlodar",
    "павлодар",
    "uralsk",
    "уральск",
    "taraz",
    "тараз",
}


def _is_kazakhstan_location(location: str) -> bool:
    text = (location or "").lower()
    return any(keyword in text for keyword in KAZAKHSTAN_LOCATION_KEYWORDS)


def _atyrau_priority(location: str) -> int:
    text = (location or "").lower()
    return 0 if ("atyrau" in text or "атырау" in text) else 1


def _score_job(job: Vacancy, skill_names: set[str], interests: set[str], goal: str, query: str) -> int:
    text = " ".join(
        [
            job.role,
            job.company,
            job.description,
            job.source_program,
            " ".join(job.tags or []),
        ]
    ).lower()
    skill_hits = sum(1 for s in skill_names if s in text)
    interest_hits = sum(1 for i in interests if i in text)
    goal_bonus = 12 if goal and goal in text else 0
    query_bonus = 10 if query and query in text else 0
    return max(45, min(99, 48 + skill_hits * 10 + interest_hits * 7 + goal_bonus + query_bonus))


def build_job_matches(profile: Profile | None, skills: list[Skill], *, query: str | None = None) -> list[dict]:
    skill_names = _normalize([skill.name for skill in skills])
    interests = _normalize(profile.interests if profile else [])
    goal = (profile.career_goal if profile else "").strip().lower()
    normalized_query = (query or goal or "").strip().lower()
    tokens = [token for token in normalized_query.split() if len(token) > 2][:8]

    vacancies = Vacancy.objects.filter(is_active=True)
    if tokens:
        filtered = []
        for vacancy in vacancies:
            text = " ".join(
                [vacancy.role, vacancy.company, vacancy.location, vacancy.source_program, vacancy.description, " ".join(vacancy.tags)]
            ).lower()
            if any(token in text for token in tokens):
                filtered.append(vacancy)
        vacancies_list = filtered or list(vacancies)
    else:
        vacancies_list = list(vacancies)

    matches: list[dict] = []
    for vacancy in vacancies_list:
        score = _score_job(vacancy, skill_names, interests, goal, normalized_query)
        reason = vacancy.description or "Вакансия релевантна вашему профилю и академическому треку."
        matches.append(
            {
                "id": str(vacancy.id),
                "company": vacancy.company,
                "role": vacancy.role,
                "location": vacancy.location,
                "type": vacancy.employment_type,
                "salary": vacancy.salary,
                "match": score,
                "tags": vacancy.tags,
                "reason": reason,
                "url": vacancy.url,
                "source": "easytap-db",
                "source_program": vacancy.source_program,
                "category": vacancy.category,
            }
        )

    return sorted(matches, key=lambda item: (_atyrau_priority(item["location"]), -item["match"]))[:20]


def build_admin_candidates(
    profiles: list[Profile], query: str = "", min_match: int = 0, year: int | None = None
) -> list[dict]:
    q = query.strip().lower()
    candidates: list[dict] = []

    for profile in profiles:
        skills = sorted(profile.user.skills.all(), key=lambda item: item.level, reverse=True)
        top_skill = skills[0].name if skills else "Not specified"
        top_level = skills[0].level if skills else 0

        profile_text = " ".join(
            [
                profile.user.full_name,
                profile.university,
                profile.major,
                profile.career_goal,
                top_skill,
            ]
        ).lower()

        if q and q not in profile_text:
            continue
        if year is not None and profile.year != year:
            continue

        completeness = sum(
            bool(value)
            for value in [
                profile.university,
                profile.major,
                profile.career_goal,
                profile.interests,
                profile.experience,
            ]
        )
        match = min(99, 50 + completeness * 7 + round(top_level * 0.28))

        if match < min_match:
            continue

        candidates.append(
            {
                "id": str(profile.user_id),
                "name": profile.user.full_name,
                "university": profile.university,
                "major": profile.major,
                "year": profile.year,
                "top_skill": top_skill,
                "match": match,
            }
        )

    return sorted(candidates, key=lambda item: item["match"], reverse=True)
