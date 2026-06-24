from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("providers", "0005_tutor_detail_is_verified"),
    ]

    operations = [
        migrations.AddField(
            model_name="tutordetail",
            name="deleted_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="deleted at"
            ),
        ),
    ]
