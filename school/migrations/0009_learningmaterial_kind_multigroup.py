from django.db import migrations, models
import django.db.models.deletion


def forwards_create_group_links(apps, schema_editor):
    LearningMaterial = apps.get_model('school', 'LearningMaterial')
    LearningMaterialGroup = apps.get_model('school', 'LearningMaterialGroup')

    # Best-effort backfill for legacy single-group field.
    for material in LearningMaterial.objects.exclude(group_id__isnull=True).iterator():
        LearningMaterialGroup.objects.get_or_create(
            material_id=material.id,
            group_id=material.group_id,
            defaults={'is_published': bool(getattr(material, 'is_published', True))},
        )


def backwards_delete_group_links(apps, schema_editor):
    LearningMaterialGroup = apps.get_model('school', 'LearningMaterialGroup')
    LearningMaterialGroup.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('school', '0008_user_birth_date_user_first_name_user_last_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='learningmaterial',
            name='kind',
            field=models.CharField(
                choices=[('video', 'Video'), ('document', 'Document'), ('article', 'Article'), ('book', 'Book')],
                default='video',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='learningmaterial',
            name='content_text',
            field=models.TextField(blank=True, db_column='contentText', null=True),
        ),
        migrations.CreateModel(
            name='LearningMaterialGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_published', models.BooleanField(db_column='isPublished', default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='createdAt')),
                ('group', models.ForeignKey(
                    db_column='groupId',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='material_links',
                    to='school.group',
                )),
                ('material', models.ForeignKey(
                    db_column='materialId',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='group_links',
                    to='school.learningmaterial',
                )),
            ],
            options={
                'db_table': 'LearningMaterialGroups',
                'unique_together': {('material', 'group')},
            },
        ),
        migrations.RunPython(forwards_create_group_links, backwards_delete_group_links),
    ]
