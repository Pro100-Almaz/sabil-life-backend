import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("providers", "0012_providerverification_cv"),
    ]

    operations = [
        migrations.AddField(
            model_name="providerverification",
            name="ai_processing_consent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="ProviderVerificationAIScreening",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("QUEUED", "Queued"),
                            ("PROCESSING", "Processing"),
                            ("RECOMMENDED", "Recommended"),
                            ("NEEDS_REVIEW", "Needs review"),
                            ("INSUFFICIENT", "Insufficient information"),
                            ("FAILED", "Failed"),
                        ],
                        default="QUEUED",
                        max_length=20,
                    ),
                ),
                ("summary", models.TextField(blank=True)),
                ("strengths", models.JSONField(blank=True, default=list)),
                ("concerns", models.JSONField(blank=True, default=list)),
                ("missing_information", models.JSONField(blank=True, default=list)),
                ("manual_checks", models.JSONField(blank=True, default=list)),
                ("criteria", models.JSONField(blank=True, default=list)),
                (
                    "confidence",
                    models.PositiveSmallIntegerField(blank=True, null=True),
                ),
                ("provider", models.CharField(default="openai", max_length=40)),
                ("model", models.CharField(blank=True, max_length=80)),
                ("rubric_version", models.CharField(default="1.0", max_length=20)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "verification",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_screenings",
                        to="providers.providerverification",
                    ),
                ),
            ],
            options={
                "verbose_name": "AI CV screening",
                "verbose_name_plural": "AI CV screenings",
                "ordering": ["-created_at"],
            },
        ),
    ]
