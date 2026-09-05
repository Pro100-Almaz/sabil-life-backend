from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_customuser_uuid"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="deleted at"),
        ),
    ]
