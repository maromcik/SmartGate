from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from LiveView.models import Person, Log, Setting, Subscriber
from django.utils.safestring import mark_safe
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import path
from LiveView import views
from django.http import HttpResponseRedirect
from django.contrib import messages
from webpush.models import PushInformation, SubscriptionInfo
import socket


# redifines admin interface behavour
class LogAdmin(admin.ModelAdmin):
    # field options
    list_display = ['person', 'time', 'granted', 'image_tag']
    list_filter = ['time', 'granted']
    search_fields = ['person__name']
    readonly_fields = ['person', 'time', 'granted', 'snapshot']

    # you cannot change logs
    def has_add_permission(self, request, obj=None):
        return False

    # there's an image (snapshot)
    def image_tag(self, obj):
        try:
            return mark_safe('<img src="{url}" height={height} />'.format(
                url=obj.snapshot.url,
                height=150,
            )
            )
        except ValueError:
            pass

    image_tag.short_description = 'Image'


class PersonAdmin(admin.ModelAdmin):
    list_filter = ['authorized']
    search_fields = ['name']
    fields = ['name', 'authorized', 'file']
    list_display = ['name', 'authorized', 'image_tag']
    change_list_template = "LiveView/change_list.html"

    # add links to custom buttons
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('encoding/', self.run_encodings),
            path('load/', self.load_files),
        ]
        return my_urls + urls

    # add functionality to custom buttons
    @method_decorator(login_required(login_url='/admin/login'))
    def run_encodings(self, request):
        # triggers running encodings of known persons
        views.rec_threads.rec.load_files()
        views.rec_threads.rec.known_subjects_descriptors()
        views.rec_threads.rec.load_files()
        self.message_user(request, "Encodings done!")
        return HttpResponseRedirect("../")

    @method_decorator(login_required(login_url='/admin/login'))
    # load files
    def load_files(self, request):
        views.rec_threads.rec.load_files()
        self.message_user(request, "Files loaded!")
        return HttpResponseRedirect("../")

    # there's an image of known person in the fields
    def image_tag(self, obj):
        return mark_safe('<img src="{url}" height={height} />'.format(
            url=obj.file.url,
            height=150,
        )
        )

    image_tag.short_description = 'Image'


class SettingAdmin(admin.ModelAdmin):
    fields = ['device', 'crop']
    list_display = ['device', 'crop']
    change_list_template = "LiveView/change_list2.html"

    # there's only one row of settings, there are no more
    def has_add_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('grab/', self.grab_cap),
            path('load/', self.load_files),
        ]
        return my_urls + urls

    @method_decorator(login_required(login_url='/admin/login'))
    def load_files(self, request):
        views.rec_threads.rec.load_files()
        self.message_user(request, "Files loaded!")
        return HttpResponseRedirect("../")

    @method_decorator(login_required(login_url='/admin/login'))
    def grab_cap(self, request):
        # grabs capture (reconnects camera)
        try:
            if views.rec_threads.facerecognition_thread.isAlive():
                views.rec_threads.rec.load_files()
                views.rec_threads.rec.grab_cap()
                views.rec_threads.startrecognition()
                messages.success(request, "Camera reconnected!")
                return HttpResponseRedirect("../")
            else:
                messages.warning(request, "Face recognition is not running!")
                return HttpResponseRedirect("../")
        except AttributeError:
            messages.warning(request, "Face recognition is not running!")
            return HttpResponseRedirect("../")


# adds subscriber field to authenticated users table
class SubscriberInline(admin.StackedInline):
    model = Subscriber
    can_delete = False
    list_display = ['subscription']


class UserAdmin(BaseUserAdmin):
    inlines = (SubscriberInline,)


# registers all the models
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Log, LogAdmin)
admin.site.register(Setting, SettingAdmin)
# admin.site.register(SubscriptionInfo)
admin.site.site_header = "Smart Gate Administration"
