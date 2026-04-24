from __future__ import annotations

from dataclasses import dataclass

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


def build_job_matches(profile: Profile | None, skills: list[Skill]) -> list[dict]:
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
            }
        )

    return sorted(matches, key=lambda item: item["match"], reverse=True)


def build_admin_candidates(profiles: list[Profile], query: str = "") -> list[dict]:
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
