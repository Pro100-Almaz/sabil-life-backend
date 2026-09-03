import uuid

from django.db import migrations, models


def populate_user_uuids(apps, schema_editor):
    CustomUser = apps.get_model("users", "CustomUser")
    for user in CustomUser.objects.filter(uuid__isnull=True).iterator():
        user.uuid = uuid.uuid4()
        user.save(update_fields=["uuid"])


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_delete_managerdetail"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="uuid",
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
        migrations.RunPython(populate_user_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="customuser",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True
            ),
        ),
    ]
