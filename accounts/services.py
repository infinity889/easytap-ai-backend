from __future__ import annotations

from dataclasses import dataclass
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from .models import Profile, Skill


@dataclass(frozen=True)
class DemoJob:
    id: str
    company: str
    role: str
    location: str
    type: str
    salary: str
    tags: list[str]
    reason: str


DEMO_JOBS: list[DemoJob] = [
    DemoJob(
        id="job-atyrau-1",
        company="TCO",
        role="Junior Data Analyst",
        location="Atyrau",
        type="Full-time",
        salary="$1,200-$1,800",
        tags=["SQL", "Python", "Analytics"],
        reason="Локальная вакансия в Атырау для аналитического профиля.",
    ),
    DemoJob(
        id="job-ml-1",
        company="Yandex",
        role="ML Engineer Intern",
        location="Almaty",
        type="Internship",
        salary="up to $900",
        tags=["Python", "PyTorch", "NLP"],
        reason="Strong fit for machine learning and applied Python work.",
    ),
    DemoJob(
        id="job-be-1",
        company="Kaspi",
        role="Junior Backend Developer",
        location="Astana",
        type="Full-time",
        salary="$1,400-$2,000",
        tags=["Python", "Django", "PostgreSQL"],
        reason="Great entry path for backend-focused students.",
    ),
    DemoJob(
        id="job-fe-1",
        company="Freedom",
        role="Frontend Intern",
        location="Remote",
        type="Internship",
        salary="stipend",
        tags=["JavaScript", "React", "Figma"],
        reason="Strong overlap with modern web and UI skills.",
    ),
    DemoJob(
        id="job-da-1",
        company="BI Group",
        role="Data Analyst Intern",
        location="Shymkent",
        type="Internship",
        salary="$700-$1,000",
        tags=["SQL", "Python", "Analytics"],
        reason="Best for analytical profiles with data interests.",
    ),
    DemoJob(
        id="job-prod-1",
        company="Chocofamily",
        role="Product Operations Associate",
        location="Almaty",
        type="Full-time",
        salary="$1,000-$1,500",
        tags=["Product", "Communication", "English B2"],
        reason="Balanced role for multidisciplinary students.",
    ),
]


def _normalize(values: list[str]) -> set[str]:
    return {value.strip().lower() for value in values if value.strip()}


def _safe_get_json(url: str, params: dict) -> dict:
    query = urlencode({k: v for k, v in params.items() if v not in (None, "")})
    full_url = f"{url}?{query}" if query else url
    req = Request(full_url, headers={"User-Agent": "EasyTapAI/1.0"})
    with urlopen(req, timeout=settings.JOB_SEARCH_TIMEOUT) as response:
        data = response.read().decode("utf-8")
    parsed = json.loads(data)
    return parsed if isinstance(parsed, dict) else {}


def _format_salary(from_value, to_value, currency) -> str:
    if from_value and to_value:
        return f"{from_value} - {to_value} {currency}".strip()
    if from_value:
        return f"от {from_value} {currency}".strip()
    if to_value:
        return f"до {to_value} {currency}".strip()
    return "не указана"


def _extract_query_candidates(query: str) -> list[str]:
    text = " ".join(query.lower().split())
    aliases = {
        "фуллстек": ["full stack developer", "fullstack developer", "web developer"],
        "фулстек": ["full stack developer", "fullstack developer"],
        "frontend": ["frontend developer", "react developer"],
        "backend": ["backend developer", "python developer"],
        "стажировк": ["intern", "internship", "junior"],
    }
    result = [text]
    for key, values in aliases.items():
        if key in text:
            result.extend(values)
    unique: list[str] = []
    seen: set[str] = set()
    for item in result:
        cleaned = item.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        unique.append(cleaned)
    return unique[:6] or ["junior developer internship"]


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


def _search_hh(query: str, city: str | None = None, limit: int = 5) -> list[dict]:
    try:
        text = f"{query} {city}".strip() if city else query
        payload = _safe_get_json(
            f"{settings.HH_API_URL.rstrip('/')}/vacancies",
            {
                "text": text,
                "per_page": max(1, min(limit, 20)),
                "page": 0,
                "order_by": "relevance",
            },
        )
        items = payload.get("items", [])
        results: list[dict] = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            salary = item.get("salary") or {}
            results.append(
                {
                    "id": str(item.get("id") or f"hh-{len(results)}"),
                    "company": str((item.get("employer") or {}).get("name") or "Компания"),
                    "role": str(item.get("name") or "Без названия"),
                    "location": str((item.get("area") or {}).get("name") or "Не указано"),
                    "type": "Full-time",
                    "salary": _format_salary(salary.get("from"), salary.get("to"), salary.get("currency") or ""),
                    "tags": [],
                    "reason": "Найдено на HH по твоему запросу.",
                    "url": str(item.get("alternate_url") or ""),
                    "source": "hh.ru",
                }
            )
        return results
    except Exception:
        return []


def _search_remotive(query: str, limit: int = 5) -> list[dict]:
    try:
        payload = _safe_get_json(
            f"{settings.REMOTIVE_API_URL.rstrip('/')}/remote-jobs",
            {"search": query, "limit": max(1, min(limit, 20))},
        )
        items = payload.get("jobs", [])
        results: list[dict] = []
        for item in items[:limit]:
            if not isinstance(item, dict):
                continue
            location = str(item.get("candidate_required_location") or "Remote")
            if not _is_kazakhstan_location(location):
                continue
            results.append(
                {
                    "id": str(item.get("id") or f"remotive-{len(results)}"),
                    "company": str(item.get("company_name") or "Компания"),
                    "role": str(item.get("title") or "Без названия"),
                    "location": location,
                    "type": "Remote",
                    "salary": str(item.get("salary") or "не указана"),
                    "tags": [],
                    "reason": "Найдено на Remotive как дополнительный источник.",
                    "url": str(item.get("url") or ""),
                    "source": "remotive.com",
                }
            )
        return results
    except Exception:
        return []


def _score_job(job: dict, skill_names: set[str], interests: set[str], goal: str) -> int:
    text = " ".join(
        [
            str(job.get("role") or ""),
            str(job.get("company") or ""),
            str(job.get("reason") or ""),
            " ".join(job.get("tags") or []),
        ]
    ).lower()
    skill_hits = sum(1 for s in skill_names if s in text)
    interest_hits = sum(1 for i in interests if i in text)
    goal_bonus = 12 if goal and goal in text else 0
    return max(60, min(99, 62 + skill_hits * 9 + interest_hits * 5 + goal_bonus))


def _demo_matches(profile: Profile | None, skills: list[Skill]) -> list[dict]:
    skill_names = _normalize([skill.name for skill in skills])
    interests = _normalize(profile.interests if profile else [])
    goal = (profile.career_goal if profile else "").strip().lower()

    matches: list[dict] = []
    for job in DEMO_JOBS:
        job_tags = _normalize(job.tags)
        overlap = len(skill_names & job_tags)
        interest_overlap = len(interests & job_tags)

        score = 55 + overlap * 12 + interest_overlap * 6
        if goal and (goal in job.role.lower() or any(goal_part in job.role.lower() for goal_part in goal.split())):
            score += 10
        if profile and profile.onboarded:
            score += 4
        score = max(60, min(score, 99))

        matches.append(
            {
                "id": job.id,
                "company": job.company,
                "role": job.role,
                "location": job.location,
                "type": job.type,
                "salary": job.salary,
                "match": score,
                "tags": job.tags,
                "reason": job.reason,
                "url": "",
                "source": "demo",
            }
        )

    return sorted(matches, key=lambda item: item["match"], reverse=True)


def build_job_matches(profile: Profile | None, skills: list[Skill], *, query: str | None = None) -> list[dict]:
    skill_names = _normalize([skill.name for skill in skills])
    interests = _normalize(profile.interests if profile else [])
    goal = (profile.career_goal if profile else "").strip().lower()

    search_query = (query or goal or "junior intern web developer").strip()
    query_candidates = _extract_query_candidates(search_query)
    city = None
    lowered = search_query.lower()
    if "алматы" in lowered:
        city = "Алматы"
    elif "астана" in lowered:
        city = "Астана"
    elif "казахстан" in lowered:
        city = "Казахстан"

    merged: list[dict] = []
    seen: set[str] = set()

    def add_items(items: list[dict]) -> None:
        for item in items:
            key = item.get("url") or f"{item.get('company')}:{item.get('role')}:{item.get('location')}"
            if key in seen:
                continue
            seen.add(key)
            item["match"] = _score_job(item, skill_names, interests, goal)
            if not item.get("tags"):
                item["tags"] = [t for t in [goal, "career", "job"] if t]
            merged.append(item)

    for candidate in query_candidates:
        add_items(_search_hh(candidate, city=city, limit=4))
        if len(merged) >= 8:
            break

    if len(merged) < 4:
        for candidate in query_candidates[:3]:
            add_items(_search_remotive(candidate, limit=3))
            if len(merged) >= 8:
                break

    # Keep only Kazakhstan vacancies, with Atyrau first.
    merged = [item for item in merged if _is_kazakhstan_location(str(item.get("location") or ""))]

    if not merged:
        demo = [item for item in _demo_matches(profile, skills) if _is_kazakhstan_location(item["location"])]
        return sorted(demo, key=lambda item: (_atyrau_priority(item["location"]), -item["match"]))

    return sorted(merged, key=lambda item: (_atyrau_priority(str(item.get("location") or "")), -item["match"]))


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
