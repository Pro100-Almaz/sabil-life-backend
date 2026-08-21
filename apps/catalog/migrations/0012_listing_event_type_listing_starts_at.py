from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0011_listing_registration_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("ONE_TIME", "One-time event"),
                    ("ONGOING", "Ongoing masterclass"),
                ],
                default="ONGOING",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="starts_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
