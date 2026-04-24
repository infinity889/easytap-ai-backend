from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_vacancy"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="vacancy",
            index=models.Index(fields=["is_active", "category"], name="vacancy_active_category_idx"),
        ),
        migrations.AddIndex(
            model_name="vacancy",
            index=models.Index(fields=["is_active", "location"], name="vacancy_active_location_idx"),
        ),
        migrations.AddIndex(
            model_name="vacancy",
            index=models.Index(fields=["is_active", "employment_type"], name="vacancy_active_type_idx"),
        ),
    ]
