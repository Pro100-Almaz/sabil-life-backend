"""
Redesign Inquiry around tutors instead of listings.

Inquiries no longer reference a Listing or a denormalized provider; a family
now addresses a specific tutor via that tutor's TutorDetail profile. Existing
rows reference listings and have no tutor counterpart, so they are cleared
before the non-nullable `tutor` FK is added. Adds the CANCELLED status used by
the family-initiated cancel flow.
"""

import django.db.models.deletion
from django.db import migrations, models


def clear_inquiries(apps, schema_editor):
    Inquiry = apps.get_model("inquiries", "Inquiry")
    Inquiry.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("inquiries", "0001_initial"),
        ("providers", "0008_delete_providerprofile"),
    ]

    operations = [
        migrations.RunPython(clear_inquiries, migrations.RunPython.noop),
        migrations.RemoveField(model_name="inquiry", name="listing"),
        migrations.RemoveField(model_name="inquiry", name="provider"),
        migrations.AddField(
            model_name="inquiry",
            name="tutor",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="inquiries",
                to="providers.tutordetail",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="inquiry",
            name="status",
            field=models.CharField(
                choices=[
                    ("NEW", "New"),
                    ("CONTACTED", "Contacted"),
                    ("ACCEPTED", "Accepted"),
                    ("DECLINED", "Declined"),
                    ("COMPLETED", "Completed"),
                    ("CANCELLED", "Cancelled"),
                ],
                db_index=True,
                default="NEW",
                max_length=16,
            ),
        ),
    ]
