from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_telegramlink"),
    ]

    operations = [
        migrations.CreateModel(
            name="AssistantMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("channel", models.CharField(choices=[("web", "Web"), ("telegram", "Telegram")], max_length=20)),
                ("external_user_id", models.CharField(blank=True, db_index=True, max_length=64)),
                ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant")], max_length=20)),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assistant_messages",
                        to="accounts.user",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
