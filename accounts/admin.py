from django.contrib import admin
from .models import User, seekerdb, employerdb, Job, Application, Notification

admin.site.register(User)
admin.site.register(seekerdb)
admin.site.register(employerdb)
admin.site.register(Job)
admin.site.register(Notification)

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('seeker', 'job', 'status', 'applied_at')
    list_filter = ('status', 'applied_at')
    search_fields = ('seeker__full_name', 'job__job_role')