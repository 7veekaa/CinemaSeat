from django.contrib import admin
from django.apps import apps
from django.contrib.admin.sites import AlreadyRegistered

def _autoreg(app_label):
    try:
        for model in apps.get_app_config(app_label).get_models():
            try:
                admin.site.register(model)
            except AlreadyRegistered:
                pass
    except LookupError:
        # app not installed or doesn't exist — ignore
        pass

_autoreg('users')
_autoreg('cinema')
