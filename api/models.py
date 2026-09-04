from django.db import models

class Eps(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=255)
    nit = models.CharField(max_length=50, blank=True, null=True)
    regimen = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Cie10(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField()
    version = models.CharField(max_length=50, blank=True, null=True)
    version_fecha = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.codigo} - {self.descripcion[:50]}"

class Cups(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField()
    version = models.CharField(max_length=50, blank=True, null=True)
    version_fecha = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.codigo} - {self.descripcion[:50]}"
