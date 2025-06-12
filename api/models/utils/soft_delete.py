from django.utils import timezone
from django.db import models
from django.db.models.query import QuerySet
from rest_framework import serializers


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQueryset(self.model, using=self._db).alive()

    def all_with_deleted(self):
        return SoftDeleteQueryset(self.model, using=self._db)

    def only_deleted(self):
        return SoftDeleteQueryset(self.model, using=self._db).deleted()


class SoftDeleteMixin(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    class Meta:
        abstract = True


class SoftDeleteQueryset(QuerySet):
    def delete(self):
        return super().update(is_deleted=True, deleted_at=timezone.now())

    def hard_delete(self):
        return super().delete()

    def alive(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)


class SoftDeleteSafeModelSerializer(serializers.ModelSerializer):
    class Meta:
        abstract = True
        exclude = ["is_deleted", "deleted_at"]
