# Generated by Django 5.0.4 on 2024-07-05 18:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('terno', '0010_llmapikey'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupTableRowFilter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filter_str', models.CharField(max_length=300)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.group')),
                ('table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='terno.table')),
            ],
        ),
        migrations.DeleteModel(
            name='GroupTableRowFilterSelector',
        ),
    ]
