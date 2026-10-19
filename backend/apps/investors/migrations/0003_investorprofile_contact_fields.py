import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('investors', '0002_investorprofile_organization_type_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='investorprofile',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='investor_profiles', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='investorprofile',
            name='contact_name',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='investorprofile',
            name='contact_email',
            field=models.EmailField(blank=True, default='', max_length=254),
        ),
        migrations.AddField(
            model_name='investorprofile',
            name='contact_phone',
            field=models.CharField(blank=True, default='', max_length=32),
        ),
    ]
