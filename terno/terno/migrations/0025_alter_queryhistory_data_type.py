# Generated by Django 5.0.4 on 2024-07-31 03:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('terno', '0024_queryhistory_created_at_queryhistory_updated_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='queryhistory',
            name='data_type',
            field=models.CharField(choices=[('user_prompt', 'User Prompt'), ('generated_sql', 'Generated SQL'), ('user_executed_sql', 'User Executed SQL'), ('actual_executed_sql', 'Actual Executed SQL')], help_text='Select the type of data you want to save', max_length=64),
        ),
    ]