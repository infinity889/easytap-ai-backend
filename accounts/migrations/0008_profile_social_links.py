from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_remove_vacancy_vacancy_active_category_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="avatar_url",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="github_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="telegram_url",
            field=models.URLField(blank=True),
        ),
    ]
