from django.db import models
from django.contrib.auth.models import User


# every class represents table in the database

class Person(models.Model):
    # fields of the table
    name = models.CharField(max_length=50)
    authorized = models.BooleanField(default=False)
    file = models.ImageField(upload_to="persons/")

    # display names
    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    # display name of plural forms
    class Meta:
        verbose_name_plural = "persons"


class Log(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE, null=True)
    time = models.DateTimeField('date of attempt to access')
    granted = models.BooleanField(default=False)
    snapshot = models.ImageField(upload_to="snapshots/", blank=True)

    def __str__(self):
        try:
            return str(self.person.name)
        except AttributeError:
            return "unknown"

    class Meta:
        verbose_name_plural = "logs"


class Setting(models.Model):
    # predetermined choices
    stream1 = "rtsp://admin:M14ercedes1@192.168.1.64:554>/Streaming/Channels/101/?tcp"
    stream2 = "rtsp://192.168.1.62/user=admin&password=&channel=1&stream=0.sdp?real_stream"
    stream3 = "http://192.168.3.62:8080/video"
    stream4 = "http://192.168.3.63:8080/video"
    DEVICE_CHOICES = (
        (stream1, 'Hikvision camera'),
        (stream2, 'Gate camera'),
        (stream3, 'S7 Edge camera'),
        (stream4, 'A5 camera'),
    )

    device = models.CharField(
        max_length=255,
        choices=DEVICE_CHOICES,
        default=stream2
    )

    crop0 = '1'
    crop1 = '0.75'
    crop2 = '0.5'
    crop3 = '0.25'
    crop4 = '0.125'
    CROP_CHOICES = (
        (crop0, '1'),
        (crop1, '0.75'),
        (crop2, '0.5'),
        (crop3, '0.25'),
        (crop4, '0.125'),
    )
    crop = models.CharField(
        max_length=10,
        choices=CROP_CHOICES,
        default=crop3,
    )

    def __str__(self):
        return "device and crop"

    class Meta:
        verbose_name_plural = "settings"


# definition of subscriber field in the user model
# test write comment, it doesnt work as expected I would be better

class Subscriber(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subscription = models.BooleanField(default=False)

    def __str__(self):
        return "will receive ring notifications, if checked."

    class Meta:
        verbose_name_plural = "subscriptions"
