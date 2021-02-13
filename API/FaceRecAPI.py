# Dlib is released under Boost Software License
"""
Boost Software License - Version 1.0 - August 17th, 2003

Permission is hereby granted, free of charge, to any person or organization
obtaining a copy of the software and accompanying documentation covered by
this license (the "Software") to use, reproduce, display, distribute,
execute, and transmit the Software, and to prepare derivative works of the
Software, and to permit third-parties to whom the Software is furnished to
do so, all subject to the following:

The copyright notices in the Software and this entire statement, including
the above license grant, this restriction and the following disclaimer,
must be included in all copies of the Software, in whole or in part, and
all derivative works of the Software, unless such copies or derivative
works are solely in the form of machine-executable object code generated by
a source language processor.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT
SHALL THE COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE
FOR ANY DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

# importing needed modules
import dlib
import cv2
import numpy as np
import time
import os
import threading
from queue import Queue
from multiprocessing.pool import ThreadPool
import pickle
import socket
import string
import secrets
import LiveView.models as database
from django.utils import timezone
from LiveView import views
from webpush import send_user_notification


# Class managing face recognition, interaction with Arduino and logging to database
class FaceRecognition:
    def __init__(self, models_paths):
        # resize factor, incorrectly called crop factor in the documentation and models. It's a typo.
        self.resize_factor = float(database.Setting.objects.get(pk=1).crop)
        # device got form database
        self.device = database.Setting.objects.get(pk=1).device
        # neccessary models for shape prediction and face recognition
        self.models = models_paths
        self.dir = os.path.join(os.path.dirname(__file__), "..")
        # creates a Queue for frames got camera
        self.frameQ = Queue()

        # lists of descriptors, all names and authorized names
        self.descriptors = []
        self.names = []
        self.authorized = []

        # counts blinks in the blink detector
        self.blink_frame_count = 0
        self.frame_count = 0

        # variables for the access function
        self.auth_count = 0
        self.unknown_count = 0
        self.empty_count1 = 0
        self.empty_count2 = 0
        self.trigtime = 0

        # creating dlib objects, face detector, shape (landmark) detector and the facial recognition itself
        self.detector = dlib.get_frontal_face_detector()
        self.predictor68 = dlib.shape_predictor(self.models[2])
        self.facerec_model = dlib.face_recognition_model_v1(self.models[1])

        # async thread pool for Arduino
        self.arduino_server_pool = ThreadPool(processes=1)

        # LAN information
        self.host = "192.168.1.5"
        self.port1 = 13081
        self.ring = False

        # # loading data
        # self.persons = database.Person.objects.all()
        # self.pks = list(self.persons.values_list('id', flat=True))
        # print("primary keys have been loaded")
        # self.names = list(self.persons.values_list('name', flat=True))
        # print("names have been loaded")
        # self.authorized_pks = list(self.persons.values_list('authorized', flat=True))
        # print("authorization values have been loaded")
        # self.files = list(self.persons.values_list('file', flat=True))
        # print("images have been loaded")

    # draws the bounding rectangle to every processed frame
    def draw(self, img, rect):
        (x, y, w, h) = rect
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # prints name of the person to every processed frame
    def PrintText(self, img, text, x, y):
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 255, 0), 2)

    # resizes frames
    def resize_img(self, img, fx=0.25, fy=0.25):
        return cv2.resize(img, (0, 0), fx=fx, fy=fy)

    # convers dlib coordinates to opencv coordinates
    def dlib2opencv(self, dlib_rect):
        x = dlib_rect.left()
        y = dlib_rect.top()
        w = dlib_rect.right()
        h = dlib_rect.bottom()
        return [x, y, w - x, h - y]

    # loads static images of known persons
    def load_image(self, filename):
        img = cv2.imread(filename)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        # img = cv2.equalizeHist(img)
        return img

    # releases video capture
    def release_cap(self):
        self.cap.release()

    # grabs video capture
    def grab_cap(self):
        self.resize_factor = float(database.Setting.objects.get(pk=1).crop)
        self.device = database.Setting.objects.get(pk=1).device
        # self.device = "/home/user/PycharmProjects/resource/rebs2.mp4"
        self.cap = cv2.VideoCapture(self.device)

    # loads neccessary files
    def load_files(self):
        self.authorized = []
        self.device = database.Setting.objects.get(pk=1).device
        print("Device has been loaded")
        self.resize_factor = float(database.Setting.objects.get(pk=1).crop)
        print("crop factor has been loaded")
        self.persons = database.Person.objects.all()
        self.pks = list(self.persons.values_list('id', flat=True))
        print("primary keys have been loaded")
        self.names = list(self.persons.values_list('name', flat=True))
        print("names have been loaded")
        self.authorized_pks = list(self.persons.values_list('authorized', flat=True))
        print("authorization values have been loaded")
        self.files = list(self.persons.values_list('file', flat=True))
        print("images have been loaded")
        for name, authorized_pk in zip(self.names, self.authorized_pks):
            if authorized_pk:
                self.authorized.append(name)
        try:
            with open('descriptors.pkl', 'rb') as infile:
                self.descriptors = pickle.load(infile)
            print("descriptors have been loaded")
            infile.close()

        except FileNotFoundError:
            print("file descriptors.pkl not found")
            if input("Do you want to run the known people encoding? y/n: ").lower() == 'y':
                self.known_subjects_descriptors()
                with open('descriptors.pkl', 'rb') as infile:
                    self.descriptors = pickle.load(infile)
                print("descriptors have been loaded")
                infile.close()
            else:
                print("terminating")
                exit(101)

        return True

    # computes descriptors of known persons (all faces in the person table)
    def known_subjects_descriptors(self):
        descriptors = []
        self.dir = os.path.join(os.path.dirname(__file__), "..")
        for i in range(0, len(self.files)):
            full_path = self.dir + "/media/" + self.files[i]
            print("processing: ", full_path)
            img = self.load_image(full_path)
            face = self.detector(img, 1)
            if len(face) != 0:
                landmarks = self.predictor68(img, face[0])
                descriptors.append(np.array(self.facerec_model.compute_face_descriptor(img, landmarks)))
            else:
                print("No face in picture {}".format(full_path))
                database.Person.objects.filter(name=self.names[i]).delete()
                print("record deleted from database")

        with open('descriptors.pkl', 'wb') as outfile:
            pickle.dump(descriptors, outfile, pickle.HIGHEST_PROTOCOL)
        outfile.close()
        print("descriptors of known people has been saved")

    def write_snapshot(self, name, image, granted):
        text = ''.join(
            secrets.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in
            range(20))
        fullpath = self.dir + "/media/snapshots/" + text + ".jpg"
        djangopath = "snapshots/" + text + ".jpg"
        # save snapshot
        if cv2.imwrite(fullpath, image):
            print("snap saved")
        if name == "unknown":
            person = None
        else:
            person = database.Person.objects.get(name=name)
        log = database.Log.objects.create(person=person, time=timezone.now(), granted=granted,
                                          snapshot=djangopath)
        log.save()

    # detects faces in frames
    def detect(self, img):
        faces = self.detector(img, 1)
        if len(faces) != 0:
            return faces
        else:
            return None

    # finds landmarks in frames using the shape predictor
    def find_landmarks(self, img, faces):
        landmarks = []
        for face in faces:
            landmarks.append(self.predictor68(img, face))
        return landmarks

    # computes descriptors
    def descriptor(self, img, landmarks):
        return np.array(self.facerec_model.compute_face_descriptor(img, landmarks))

    # compares 2 faces in 128D space
    def compare(self, known, unknown):
        # the commented code is an alternative version for explanatory reasons, gives the same results
        # all = []
        # for x in known:
        #     temp = 0
        #     for y in range(len(x)):
        #         temp = (x[y]-unknown[y])**2 + temp
        #     all.append(math.sqrt(temp))
        # print(all)
        return np.linalg.norm(known - unknown, axis=1)

    # reads stream from a camera, runs neccessary image processings and puts every frame to frameQ
    def read_stream(self):
        this_frame = True
        ret = True
        while not views.rec_threads.stream_thread.stopped() and ret:
            ret, frame = self.cap.read()
            if frame is not None:
                # process every other frame
                if this_frame:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.frameQ.put(frame)
                this_frame = not this_frame
        return

    # main function, puts everything needed for facial rec. together
    def process(self):
        labels = []
        crop = None
        image = self.frameQ.get()
        frame = self.resize_img(image, fx=self.resize_factor, fy=self.resize_factor)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        faces = self.detect(frame)
        # if there are any faces in the frame
        if faces is not None:
            landmarks = self.find_landmarks(frame, faces)
            # for every faces do following
            for i in range(0, len(faces)):
                # convert coordinate systems
                rect = self.dlib2opencv(faces[i])
                # draw a rectangle
                self.draw(frame, rect)
                (x, y, w, h) = rect
                x = int(x * (1 / self.resize_factor))
                y = int(y * (1 / self.resize_factor))
                w = int(w * (1 / self.resize_factor))
                h = int(h * (1 / self.resize_factor))
                crop = image[y: y + h, x: x + w]
                # create list of comparisons by comparing the tested faces against every face in the database
                comparisons = (self.compare(self.descriptors, self.descriptor(frame, landmarks[i]))).tolist()
                # do for every comparison in the list comparisons

                if np.amin(comparisons) <= 0.55:
                    label = np.argmin(comparisons)
                    labels.append(self.blink_detector(landmarks[i], label))
                else:
                    label = None
                    labels.append(label)
                try:
                    self.PrintText(frame, self.names[int(label)], rect[0], rect[1])
                except IndexError:
                    print("Person does not exist anymore, you have most likely forgotten to load files.")
                except TypeError:
                    self.PrintText(frame, "unknown", rect[0], rect[1])
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        # self.outputQ.put(frame)
        # cv2.imshow("SmartGate", image)
        # cv2.waitKey(1)
        return labels, frame, crop

    def blink_detector(self, landmark, label):
        # create 2-item lists of 6 specific points on an eye from landmarks and convert it to numpy arrays
        p1 = np.array([landmark.parts()[36].x, landmark.parts()[36].y])
        p2 = np.array([landmark.parts()[37].x, landmark.parts()[37].y])
        p3 = np.array([landmark.parts()[38].x, landmark.parts()[38].y])
        p4 = np.array([landmark.parts()[39].x, landmark.parts()[39].y])
        p5 = np.array([landmark.parts()[40].x, landmark.parts()[40].y])
        p6 = np.array([landmark.parts()[41].x, landmark.parts()[41].y])
        # find euclidean distance between specific pairs of those points
        p2p6 = np.linalg.norm(p2 - p6)
        p3p5 = np.linalg.norm(p3 - p5)
        p1p4 = np.linalg.norm(p1 - p4)
        # compute eye aspect ratio
        EAR = (p2p6 + p3p5) / (2 * p1p4)
        # if the EAR is smaller than experimentally chosen threshlod a person has closed eyes in the frame
        if EAR < 0.21:
            self.blink_frame_count += 1
        # or she/he doesn't
        else:
            self.frame_count += 1

        # if the person has closed eyes in 2 frames and open in 3 we consider this to be a blink. return true
        # and reset the variables
        if self.blink_frame_count >= 2 and self.frame_count >= 3:
            self.blink_frame_count = 0
            self.frame_count = 0
            return label, True
        else:
            return label, False

    # manages access and writes logs to database

    def access(self, labels, image, lock):
        # if no face in frame
        if not labels:
            self.empty_count1 += 1
            self.empty_count2 += 1
            return
        for label in labels:
            # if label is none (the person is unknown)
            if label is None:
                self.unknown_count += 1
                # protection against continual writing to database if the person is in front of the camera
                # for longer period of time, process only in person ringed the bell.
                if (self.empty_count1 > 13) and self.unknown_count > 8:
                    print("unknown")
                    self.unknown_count = 0
                    self.empty_count1 = 0
                    self.write_snapshot("unknown", image, False)
                    self.ring = False
            else:
                # if the person is authorized and blinked
                if self.names[label[0]] in self.authorized:
                    if label[1]:
                        if time.time() - self.trigtime >= 2:
                            self.trigtime = time.time()
                            name = self.names[label[0]]
                            # give access, by calling open function
                            print("access has been granted for: ", name)
                            self.write_snapshot(name, image, True)
                            self.arduino_server_pool.apply_async(self.arduino_open, args=(name, lock,))
                else:
                    # again protection against continual writing
                    self.auth_count += 1
                    if (self.empty_count2 > 10) and self.auth_count > 5:
                        self.empty_count2 = 0
                        self.auth_count = 0
                        name = self.names[label[0]]
                        print("access denied for: ", name)
                        self.write_snapshot(name, image, False)
                        # sent push notification to every subscribed user with name of the person
                        for subscriber in database.Subscriber.objects.all():
                            if subscriber.subscription:
                                user = subscriber.user
                                print(subscriber.user)
                                print(subscriber.subscription)
                                payload = {'head': 'ring', 'body': name + ' is here'}
                                try:
                                    send_user_notification(user=user, payload=payload, ttl=1000)
                                except TypeError:
                                    print("push typerror")
                            else:
                                print("User not subscribed")

    def arduino_open(self, name, lock):
        # arduino client running in arduino thread, create unix socket interface
        command = "open"
        lock.acquire()
        print("connecting to: ", self.host)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.host, self.port1))
                print("Connected to arduino")
                s.sendall(b'openn')
                data = s.recv(5).decode('utf-8').rstrip('\x00').strip()
                if data == command:
                    print("gate opened")
                    # if name != "manual":
                    #     person = database.Person.objects.get(name=name)
                    #     log = database.Log.objects.create(person=person, time=timezone.now(), granted=True,
                    #                                       snapshot=None)
                    #     log.save()
                s.shutdown(1)
                s.close()
            print("connection closed")
        except OSError:
            print("cant connect to arduino")
            lock.release()
            raise OSError
        time.sleep(2)
        lock.release()
        return