from django import forms
from django.contrib.auth.models import User
from .models import *  # Replace with your actual model

class UserModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.email} - {obj.first_name}"

class DigitizingOrderForm(forms.ModelForm):
    user = UserModelChoiceField(queryset=User.objects.all())

    class Meta:
        model = DigitizingOrder
        fields = '__all__'
