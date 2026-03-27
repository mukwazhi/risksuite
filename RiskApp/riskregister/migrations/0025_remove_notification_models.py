from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('riskregister', '0024_riskowner_user'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Notification',
        ),
        migrations.DeleteModel(
            name='NotificationPreference',
        ),
        migrations.DeleteModel(
            name='NotificationRule',
        ),
    ]
