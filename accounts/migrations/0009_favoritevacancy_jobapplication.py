from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_profile_social_links"),
    ]

    operations = [
        migrations.CreateModel(
            name="FavoriteVacancy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorite_vacancies", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "vacancy",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="favorited_by", to="accounts.vacancy"),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="JobApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("planned", "Planned"),
                            ("applied", "Applied"),
                            ("interview", "Interview"),
                            ("offer", "Offer"),
                            ("rejected", "Rejected"),
                        ],
                        default="planned",
                        max_length=20,
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="job_applications", to=settings.AUTH_USER_MODEL),
                ),
                (
                    "vacancy",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="applications", to="accounts.vacancy"),
                ),
            ],
            options={
                "ordering": ["-updated_at", "-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="favoritevacancy",
            constraint=models.UniqueConstraint(fields=("user", "vacancy"), name="unique_favorite_per_user"),
        ),
        migrations.AddConstraint(
            model_name="jobapplication",
            constraint=models.UniqueConstraint(fields=("user", "vacancy"), name="unique_application_per_user"),
        ),
    ]
