from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_alter_user_groups"),
    ]

    operations = [
        migrations.CreateModel(
            name="TelegramLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tg_user_id", models.BigIntegerField(unique=True)),
                ("tg_username", models.CharField(blank=True, max_length=64)),
                ("tg_full_name", models.CharField(blank=True, max_length=120)),
                ("link_code", models.CharField(blank=True, db_index=True, max_length=12)),
                ("code_expires_at", models.DateTimeField(blank=True, null=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="telegram_link",
                        to="accounts.user",
                    ),
                ),
            ],
        ),
    ]
