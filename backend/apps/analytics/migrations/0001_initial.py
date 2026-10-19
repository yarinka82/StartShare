from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("profiles", "0001_initial"),
        ("investors", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("interested", "Interested"), ("declined", "Declined")], max_length=32)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("investor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="event_logs", to="investors.investorprofile")),
                ("startup", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="event_logs", to="profiles.startupprofile")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
