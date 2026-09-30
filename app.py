"""Initialize SQLite, then serve the local application in one process."""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

if __name__ == "__main__":
    import django
    django.setup()

    from django.core.management import call_command
    from waitress import serve
    call_command("migrate", interactive=False)
    call_command("collectstatic", interactive=False, verbosity=0)
    from config.wsgi import application

    port = int(os.environ.get("PORT", "8000"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535.")
    print(f"Bassline ready at http://localhost:{port}", flush=True)
    serve(application, host="0.0.0.0", port=port, threads=4)
