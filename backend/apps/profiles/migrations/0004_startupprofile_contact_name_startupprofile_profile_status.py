from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0003_startupprofile_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='startupprofile',
            name='contact_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='startupprofile',
            name='profile_status',
            field=models.CharField(choices=[('DRAFT', 'Draft'), ('LIVE', 'Live'), ('PAUSED', 'Paused'), ('REMOVED', 'Removed')], default='DRAFT', max_length=16),
        ),
    ]
