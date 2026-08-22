from django.db import migrations, models


def clear_non_masterclass_event_fields(apps, schema_editor):
    listing = apps.get_model("catalog", "Listing")
    listing.objects.exclude(category="MASTERCLASSES").update(
        is_online=False,
        meeting_url="",
        registration_url="",
        event_type="ONGOING",
        starts_at=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0014_listingcontact"),
    ]

    operations = [
        migrations.AlterField(
            model_name="listing",
            name="is_online",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(
            clear_non_masterclass_event_fields,
            migrations.RunPython.noop,
        ),
    ]
