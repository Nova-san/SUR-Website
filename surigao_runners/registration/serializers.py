from rest_framework import serializers
from .models import Event, Distance, Runner

class DistanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distance
        fields = ['id', 'label', 'fee']

class EventSerializer(serializers.ModelSerializer):
    distances = DistanceSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = ['id', 'name', 'date', 'description', 'poster', 'distances']

class RunnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Runner
        fields = [
            'event', 'distance', 'name', 'email', 'contact_number',
            'age', 'gender', 'shirt_size',
            'emergency_contact_name', 'emergency_contact_number',
            'proof_of_payment'
        ]
