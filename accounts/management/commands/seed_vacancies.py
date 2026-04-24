from __future__ import annotations

import random

from django.core.management.base import BaseCommand

from accounts.models import Vacancy


class Command(BaseCommand):
    help = "Seed demo vacancies for local database."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=150, help="How many vacancies to create.")

    def handle(self, *args, **options):
        count = max(1, int(options["count"]))
        created = 0

        companies = [
            "Kaspi Tech",
            "Kolesa Group",
            "Air Astana Digital",
            "Freedom Holding IT",
            "Halyk FinTech",
            "Jusan Tech",
            "InDrive",
            "EPAM Kazakhstan",
            "DataArt KZ",
            "Choco Family",
            "Yandex Kazakhstan",
            "BI Group Digital",
            "Astana Hub Resident",
            "KBTU Labs",
            "Nazarbayev University Research Center",
        ]
        roles = [
            "Junior Frontend Developer",
            "Junior Backend Developer",
            "Junior Data Analyst",
            "Junior QA Engineer",
            "DevOps Intern",
            "Data Science Intern",
            "ML Engineer Intern",
            "Business Analyst Intern",
            "Python Developer Intern",
            "Support Engineer",
        ]
        locations = [
            "Almaty, Kazakhstan",
            "Astana, Kazakhstan",
            "Atyrau, Kazakhstan",
            "Shymkent, Kazakhstan",
            "Remote, Kazakhstan",
        ]
        employment_types = ["Full-time", "Part-time", "Internship", "Hybrid"]
        tags_pool = [
            "python",
            "django",
            "react",
            "typescript",
            "sql",
            "docker",
            "linux",
            "analytics",
            "excel",
            "machine learning",
            "api",
            "testing",
        ]
        categories = ["IT", "Наука и инженерия", "Бизнес и аналитика", "Образование"]

        for i in range(count):
            role = random.choice(roles)
            company = random.choice(companies)
            location = random.choice(locations)
            employment_type = random.choice(employment_types)
            salary = f"{random.randint(180, 650)}k KZT"
            tags = random.sample(tags_pool, k=random.randint(3, 5))
            category = random.choice(categories)
            program_code = f"ET-{i + 1:04d}"

            Vacancy.objects.create(
                company=company,
                role=role,
                location=location,
                employment_type=employment_type,
                salary=salary,
                tags=tags,
                description=(
                    f"{role} in {company}. We are looking for a motivated specialist with strong "
                    f"learning mindset and interest in {', '.join(tags[:2])}."
                ),
                source_program=f"EasyTap Talent Pool {random.randint(1, 12)}",
                program_code=program_code,
                program_level="junior",
                category=category,
                url=f"https://jobs.easytap.ai/vacancies/{program_code.lower()}",
                is_active=True,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} vacancies."))
