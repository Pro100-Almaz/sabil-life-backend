from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("providers", "0011_alter_tutordetail_age_groups"),
    ]

    operations = [
        migrations.AddField(
            model_name="providerverification",
            name="cv",
            field=models.FileField(
                blank=True,
                help_text="Required PDF CV for masterclass provider applications.",
                upload_to="provider-verifications/cvs/%Y/%m/",
                verbose_name="CV",
            ),
        ),
    ]
