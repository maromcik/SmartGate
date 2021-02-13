from django.http.response import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_GET, require_POST
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.conf import settings
from django.contrib.auth.decorators import login_required
from webpush import send_user_notification
from LiveView import views
from LiveView.models import Subscriber


@login_required(login_url='/accounts/login')
@require_GET
# renders home page
def home(request):
    # keys for push notifications
    webpush_settings = getattr(settings, 'WEBPUSH_SETTINGS', {})
    vapid_key = webpush_settings.get('VAPID_PUBLIC_KEY')
    user = request.user
    try:
        running = views.rec_threads.facerecognition_thread.isAlive()
    except AttributeError:
        running = False
    subscription = Subscriber.objects.get(user=user).subscription
    return render(request, 'home.html',
                  {user: user, 'vapid_key': vapid_key, 'running': running, 'subscription': subscription})


@login_required(login_url='/accounts/login')
# subscribe to push notifications

def subscribe(request):
    user = request.user

    try:
        running = views.rec_threads.facerecognition_thread.isAlive()
    except AttributeError:
        running = False
    # writes the subscription info to the database
    subscriber = Subscriber.objects.get(user=user)
    subscriber.subscription = True
    subscriber.save()
    subscription = Subscriber.objects.get(user=user).subscription
    return render(request, 'home.html', {user: user, 'subscription': subscription, 'running': running})


@login_required(login_url='/accounts/login')
# same principle, but unsubcsribe
def unsubscribe(request):
    user = request.user
    try:
        running = views.rec_threads.facerecognition_thread.isAlive()
    except AttributeError:
        running = False
    subscriber = Subscriber.objects.get(user=user)
    subscriber.subscription = False
    subscriber.save()
    subscription = Subscriber.objects.get(user=user).subscription
    return render(request, 'home.html', {user: user, 'subscription': subscription, 'running': running})
