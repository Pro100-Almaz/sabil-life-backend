from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0012_listing_event_type_listing_starts_at"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="listing",
            index=models.Index(
                fields=["category", "event_type", "status", "starts_at"],
                name="listing_expiry_idx",
            ),
        ),
    ]
