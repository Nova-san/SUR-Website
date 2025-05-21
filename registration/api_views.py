from rest_framework import generics
from datetime import date
from .models import Event, Runner
from .serializers import EventSerializer, RunnerSerializer

class EventListAPI(generics.ListAPIView):
    queryset = Event.objects.filter(date__gte=date.today()).order_by('date')
    serializer_class = EventSerializer

class RunnerCreateAPI(generics.CreateAPIView):
    queryset = Runner.objects.all()
    serializer_class = RunnerSerializer
