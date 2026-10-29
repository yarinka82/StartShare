from django.db import migrations


class Migration(migrations.Migration):
    """Step 3/3: drop the old foreign keys and dictionary tables, give the new columns their final names."""

    dependencies = [("profiles", "0004_choices_copy_data")]

    operations = [
        migrations.RemoveField(model_name="startupprofile", name="sector"),
        migrations.RemoveField(model_name="startupprofile", name="stage"),
        migrations.RemoveField(model_name="startupprofile", name="business_model"),
        migrations.RenameField(model_name="startupprofile", old_name="sector_code", new_name="sector"),
        migrations.RenameField(model_name="startupprofile", old_name="stage_code", new_name="stage"),
        migrations.RenameField(model_name="startupprofile", old_name="business_model_code", new_name="business_model"),
        migrations.DeleteModel(name="Sector"),
        migrations.DeleteModel(name="Stage"),
        migrations.DeleteModel(name="BusinessModel"),
    ]
