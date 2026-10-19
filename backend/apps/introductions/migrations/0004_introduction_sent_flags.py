from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('introductions', '0003_startupintrodecisionlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='introduction',
            name='sent_to_investor',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='introduction',
            name='sent_to_startup',
            field=models.BooleanField(default=False),
        ),
    ]
