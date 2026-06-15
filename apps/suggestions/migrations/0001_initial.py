import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceSuggestion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("SCHOOLS", "Schools"),
                            ("NURSERIES", "Nurseries"),
                            ("ACTIVITIES", "Activities"),
                            ("ENTERTAINMENT", "Entertainment"),
                            ("TUTORING", "Tutoring"),
                            ("MASTERCLASSES", "Masterclasses"),
                            ("PARTNERSHIPS", "Partnerships"),
                        ],
                        default="",
                        max_length=32,
                    ),
                ),
                (
                    "neighborhood",
                    models.CharField(blank=True, default="", max_length=120),
                ),
                ("message", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("NEW", "New"),
                            ("REVIEWED", "Reviewed"),
                            ("ACTED_ON", "Acted on"),
                            ("DISMISSED", "Dismissed"),
                        ],
                        db_index=True,
                        default="NEW",
                        max_length=16,
                    ),
                ),
                ("admin_notes", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "family",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="suggestions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
