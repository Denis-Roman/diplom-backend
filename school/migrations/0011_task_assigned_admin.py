from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0010_learningmaterial_folders'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='assigned_admin',
            field=models.ForeignKey(
                blank=True,
                db_column='assignedAdminId',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_tasks',
                to='school.user',
            ),
        ),
    ]
