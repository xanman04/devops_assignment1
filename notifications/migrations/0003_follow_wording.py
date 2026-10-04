from django.db import migrations
from django.db.models import Value
from django.db.models.functions import Concat, Substr

OLD = "A tracked event changed:"
NEW = "An event you follow changed:"


def reword(apps, schema_editor):
    """Notification text is stored when it is created, so older rows still say "tracked"."""
    Notification = apps.get_model("notifications", "Notification")
    Notification.objects.filter(summary__startswith=OLD).update(
        summary=Concat(Value(NEW), Substr("summary", len(OLD) + 1)))


class Migration(migrations.Migration):
    dependencies = [("notifications", "0002_remove_notification_notification_source_matches_kind_and_more")]
    operations = [migrations.RunPython(reword, migrations.RunPython.noop)]
