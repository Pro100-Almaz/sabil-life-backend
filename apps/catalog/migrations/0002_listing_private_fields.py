from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="session_schedule",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="listing",
            name="exact_address",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="listing",
            name="materials_required",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
