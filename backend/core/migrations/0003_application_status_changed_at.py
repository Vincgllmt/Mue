from django.db import migrations, models
from django.db.models import F
import django.utils.timezone


def backfill(apps, schema_editor):
    # Meilleure approximation pour l'existant : la dernière modification de la candidature.
    apps.get_model("core", "Application").objects.update(status_changed_at=F("updated_at"))


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_audit_revision'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='status',
            field=models.CharField(choices=[('brouillon', 'Brouillon'), ('non_postule', 'Non postulé'), ('envoyee', 'Envoyée'), ('entretien', 'Entretien'), ('refus', 'Refus')], default='brouillon', max_length=20),
        ),
        migrations.AddField(
            model_name='application',
            name='status_changed_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
