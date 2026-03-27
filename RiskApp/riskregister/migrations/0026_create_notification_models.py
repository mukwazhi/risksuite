# Generated migration to create NotificationPreference model
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('riskregister', '0025_remove_notification_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enable_email_notifications', models.BooleanField(default=True)),
                ('enable_pending_assessments', models.BooleanField(default=True)),
                ('enable_upcoming_assessments', models.BooleanField(default=True)),
                ('enable_overdue_assessments', models.BooleanField(default=True)),
                ('upcoming_days_assessment', models.PositiveIntegerField(default=2, help_text='How many days ahead to consider an assessment "upcoming"')),
                ('enable_pending_mitigations', models.BooleanField(default=True)),
                ('enable_upcoming_mitigations', models.BooleanField(default=True)),
                ('enable_overdue_mitigations', models.BooleanField(default=True)),
                ('upcoming_days_mitigation', models.PositiveIntegerField(default=2, help_text='How many days ahead to consider a mitigation "upcoming"')),
                ('notify_time', models.TimeField(blank=True, null=True)),
                ('frequency', models.CharField(choices=[('daily', 'Daily'), ('weekly', 'Weekly')], default='daily', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification_preference', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
