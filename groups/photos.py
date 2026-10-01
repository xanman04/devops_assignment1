"""Group-photo preparation kept as a stable entry point for the group service."""
from config.images import prepare_image


def prepare_photo(upload):
    return prepare_image(upload, kind="photo")
