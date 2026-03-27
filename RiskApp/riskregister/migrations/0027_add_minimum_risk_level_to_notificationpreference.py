# Generated migration to add minimum_risk_level to NotificationPreference
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('riskregister', '0026_create_notification_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationpreference',
            name='minimum_risk_level',
            field=models.CharField(choices=[('low','Low'),('medium','Medium'),('high','High'),('critical','Critical')], default='low', max_length=10, help_text='Admin: minimum risk level to trigger notifications'),
        ),
    ]
