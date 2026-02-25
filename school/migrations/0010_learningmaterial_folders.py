from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0009_learningmaterial_kind_multigroup'),
    ]

    operations = [
        migrations.CreateModel(
            name='LearningMaterialFolder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='createdAt')),
            ],
            options={
                'db_table': 'LearningMaterialFolders',
            },
        ),
        migrations.AddField(
            model_name='learningmaterial',
            name='folder',
            field=models.ForeignKey(
                blank=True,
                db_column='folderId',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='materials',
                to='school.learningmaterialfolder',
            ),
        ),
    ]
