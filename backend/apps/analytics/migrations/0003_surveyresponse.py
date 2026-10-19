import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0002_alter_eventlog_event_type'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('profiles', '0004_startupprofile_contact_name_startupprofile_profile_status'),
        ('investors', '0003_investorprofile_contact_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='SurveyResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('days_after', models.PositiveSmallIntegerField()),
                ('answer', models.CharField(blank=True, default='', max_length=32)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('investor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='survey_responses', to='investors.investorprofile')),
                ('startup', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='survey_responses', to='profiles.startupprofile')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='survey_responses', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-submitted_at']},
        ),
        migrations.AddConstraint(
            model_name='surveyresponse',
            constraint=models.UniqueConstraint(fields=('user', 'days_after'), name='uniq_survey_user_days'),
        ),
    ]
