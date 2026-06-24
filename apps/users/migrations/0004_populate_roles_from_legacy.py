from django.db import migrations

ROLES = ["FAMILY", "TUTOR", "MASTERCLASS", "MANAGER", "ADMIN"]


def populate_roles(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    CustomUser = apps.get_model("users", "CustomUser")

    role_objects = {}
    for name in ROLES:
        role_obj, _ = Role.objects.get_or_create(name=name)
        role_objects[name] = role_obj

    for user in CustomUser.objects.all():
        if user.role and user.role in role_objects:
            user.roles.add(role_objects[user.role])


def reverse_populate(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_roles_m2m_and_manager_detail"),
    ]

    operations = [
        migrations.RunPython(populate_roles, reverse_populate),
    ]
