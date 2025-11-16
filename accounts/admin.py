from django.contrib import admin
from .models import Profile, MainActuator, OrderDetails

admin.site.register(Profile)
admin.site.register(MainActuator)
admin.site.register(OrderDetails)

