from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_delete_managerdetail"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="deleted at"),
        ),
    ]
