# Generated migration for inherent risk and controls

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('riskregister', '0022_delete_assessmentdecision'),
    ]

    operations = [
        # Add inherent risk fields to Risk model
        migrations.AddField(
            model_name='risk',
            name='inherent_likelihood',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text='Inherent likelihood (1-5): Risk likelihood without controls'
            ),
        ),
        migrations.AddField(
            model_name='risk',
            name='inherent_impact',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                help_text='Inherent impact (1-5): Risk impact without controls'
            ),
        ),
        
        # Create Control model
        migrations.CreateModel(
            name='Control',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name or brief description of the control', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Detailed description of how the control works')),
                ('control_type', models.CharField(
                    choices=[
                        ('preventive', 'Preventive - Prevents risk occurrence (80% likelihood, 20% impact)'),
                        ('detective', 'Detective - Detects risk after occurrence (30% likelihood, 70% impact)'),
                        ('corrective', 'Corrective - Corrects after occurrence (10% likelihood, 90% impact)'),
                        ('directive', 'Directive - Directs behavior (50% likelihood, 50% impact)')
                    ],
                    help_text='Type of control determines how it reduces risk',
                    max_length=20
                )),
                ('effectiveness', models.DecimalField(
                    decimal_places=2,
                    default=0,
                    help_text='Control effectiveness percentage (0-100%)',
                    max_digits=5
                )),
                ('weight', models.PositiveSmallIntegerField(
                    choices=[
                        (1, '1 - Minimal importance'),
                        (2, '2 - Very low importance'),
                        (3, '3 - Low importance'),
                        (4, '4 - Below average importance'),
                        (5, '5 - Average importance'),
                        (6, '6 - Above average importance'),
                        (7, '7 - Moderately high importance'),
                        (8, '8 - High importance'),
                        (9, '9 - Very high importance'),
                        (10, '10 - Critical importance')
                    ],
                    default=5,
                    help_text='Importance/weight of this control (1-10 scale)'
                )),
                ('weight_rationale', models.TextField(
                    blank=True,
                    help_text='Explanation for why this weight was assigned'
                )),
                ('frequency', models.CharField(
                    blank=True,
                    help_text='How often the control is executed (e.g., daily, monthly, continuous)',
                    max_length=50
                )),
                ('last_tested_date', models.DateField(
                    blank=True,
                    null=True,
                    help_text='When the control was last tested'
                )),
                ('test_results', models.TextField(
                    blank=True,
                    help_text='Results from the most recent test'
                )),
                ('is_active', models.BooleanField(
                    default=True,
                    help_text='Whether this control is currently active'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('control_owner', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='owned_controls',
                    to='riskregister.riskowner'
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_controls',
                    to=settings.AUTH_USER_MODEL
                )),
                ('risk', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='controls',
                    to='riskregister.risk'
                )),
            ],
            options={
                'verbose_name': 'Control',
                'verbose_name_plural': 'Controls',
                'ordering': ['-weight', 'control_type', 'name'],
            },
        ),
    ]
