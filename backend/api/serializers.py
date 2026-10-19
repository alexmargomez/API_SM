from rest_framework import serializers
from .models import Eps, Cie10, Cups


class EpsLegacySerializer(serializers.ModelSerializer):
    """
    Serializador retrocompatible con los sistemas médicos externos (GET /api/entidades).
    Mantiene exactamente las llaves esperadas: ent_id, ent_nombre, nit, tps_rgm_nombre.
    """
    ent_id = serializers.CharField(source='codigo')
    ent_nombre = serializers.CharField(source='nombre')
    tps_rgm_nombre = serializers.CharField(source='regimen')

    class Meta:
        model = Eps
        fields = ['ent_id', 'ent_nombre', 'nit', 'tps_rgm_nombre']


class EpsPanelSerializer(serializers.ModelSerializer):
    """
    Serializador para la gestión en el panel administrativo Vue 3.
    """
    class Meta:
        model = Eps
        fields = ['id', 'codigo', 'nombre', 'nit', 'regimen']


class Cie10Serializer(serializers.ModelSerializer):
    class Meta:
        model = Cie10
        fields = ['codigo', 'descripcion', 'version', 'version_fecha']


class CupsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cups
        fields = ['codigo', 'descripcion', 'version', 'version_fecha']
