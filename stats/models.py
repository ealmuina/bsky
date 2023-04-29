from django.db import models


class Actor(models.Model):
    did = models.CharField(max_length=256, db_index=True)
    handle = models.TextField()
    display_name = models.TextField(null=True)
    description = models.TextField(null=True)
    indexed_at = models.DateTimeField(null=True)

    active = models.BooleanField(default=True)


class Follow(models.Model):
    from_actor = models.ForeignKey("Actor", on_delete=models.CASCADE, related_name="follows")
    to_actor = models.ForeignKey("Actor", on_delete=models.CASCADE, related_name="followers")

    active = models.BooleanField(default=True)
    last_seen = models.DateTimeField()
