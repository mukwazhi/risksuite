from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('riskregister', '0027_add_minimum_risk_level_to_notificationpreference'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationpreference',
            name='expiry_date',
            field=models.DateTimeField(blank=True, help_text='If set, user will be deactivated after this date/time', null=True),
        ),
    ]
