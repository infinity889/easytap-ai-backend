import uuid
from django.db import migrations, models


def seed_vacancies(apps, schema_editor):
    Vacancy = apps.get_model("accounts", "Vacancy")
    if Vacancy.objects.exists():
        return

    programs = [
        ("6B01515", "Учитель физики", "Бакалавриат", "Образование"),
        ("6В01509", "Учитель физики и информатики", "Бакалавриат", "Образование"),
        ("6В05302", "Физика-исследователь", "Бакалавриат", "Наука и инженерия"),
        ("6В07501", "Стандартизация, метрология и сертификация", "Бакалавриат", "Наука и инженерия"),
        ("7М01504", "Физика в образовании", "Магистратура", "Образование"),
        ("7М05303", "Физика и электроника", "Магистратура", "Наука и инженерия"),
        ("6B01517", "Учитель математики", "Бакалавриат", "Образование"),
        ("6B01508", "Учитель математики и физики", "Бакалавриат", "Образование"),
        ("6B05401", "Прикладное математическое моделирование", "Бакалавриат", "Наука и инженерия"),
        ("7М01503", "Управление процессом математического образования", "Магистратура", "Образование"),
        ("7M05401", "Математика и компьютерные науки", "Магистратура", "IT"),
        ("6B01513", "Информатика", "Бакалавриат", "IT"),
        ("6В06101", "Прикладная информатика в дизайне", "Бакалавриат", "IT"),
        ("6В06102", "Бизнес-аналитика и управление IT-проектами", "Бакалавриат", "Бизнес и аналитика"),
        ("6B06103", "Администрирование сетей и систем", "Бакалавриат", "IT"),
        ("7M01501", "Информатика и информатизация образования", "Магистратура", "IT"),
    ]

    companies = [
        "Kaspi Tech",
        "BI Group",
        "Freedom",
        "NIS",
        "Kcell",
    ]
    cities = ["Алматы", "Астана", "Атырау", "Шымкент", "Караганда"]
    roles = [
        ("Junior Specialist", "Полная занятость", "300000-450000 KZT"),
        ("Intern", "Стажировка", "120000-220000 KZT"),
        ("Assistant", "Частичная занятость", "180000-300000 KZT"),
        ("Research Associate", "Проектная занятость", "250000-420000 KZT"),
    ]

    created = 0
    for index, (code, program, level, category) in enumerate(programs):
        base_tags = [program.split()[0], level, category]
        for role_idx, (role_suffix, employment, salary) in enumerate(roles):
            company = companies[(index + role_idx) % len(companies)]
            city = cities[(index * 2 + role_idx) % len(cities)]
            Vacancy.objects.create(
                company=company,
                role=f"{program}: {role_suffix}",
                location=city,
                employment_type=employment,
                salary=salary,
                tags=base_tags + ["Kazakhstan", "EasyTap"],
                description=f"Вакансия связана с программой {code} ({program}) и ориентирована на студентов/выпускников.",
                source_program=f"{code} — {program}",
                program_code=code,
                program_level=level,
                category=category,
                url="",
                is_active=True,
            )
            created += 1
            if created >= 64:
                return


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_assistantmessage"),
    ]

    operations = [
        migrations.CreateModel(
            name="Vacancy",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("company", models.CharField(max_length=120)),
                ("role", models.CharField(max_length=160)),
                ("location", models.CharField(max_length=120)),
                ("employment_type", models.CharField(max_length=60)),
                ("salary", models.CharField(max_length=60)),
                ("tags", models.JSONField(blank=True, default=list)),
                ("description", models.TextField(blank=True)),
                ("source_program", models.CharField(blank=True, max_length=220)),
                ("program_code", models.CharField(blank=True, db_index=True, max_length=20)),
                ("program_level", models.CharField(blank=True, max_length=20)),
                ("category", models.CharField(blank=True, max_length=40)),
                ("url", models.URLField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["role", "company"]},
        ),
        migrations.RunPython(seed_vacancies, migrations.RunPython.noop),
    ]
