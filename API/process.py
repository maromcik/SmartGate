Process backup
    def process(self):
        labels = []
        image = self.frameQ.get()
        frame = self.resize_img(image, fx=self.resize_factor, fy=self.resize_factor)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        faces = self.detect(frame)
        #if there are any faces in the frame
        if faces is not None:
            landmarks = self.find_landmarks(frame, faces)
            #for every faces do following
            for i in range(0, len(faces)):
                #convert coordinate systems
                rect = self.dlib2opencv(faces[i])
                #draw a rectangle
                self.draw(frame, rect)
                (x, y, w, h) = rect
                x = x * 4
                y = y * 4
                w = w * 4
                h = h * 4
                crop = image[y: y + h, x: x + w]
                #create list of comparisons by comparing the tested faces against every face in the database
                comparisons = (self.compare(self.descriptors, self.descriptor(frame, landmarks[i]))).tolist()
                #do for every comparison in the list comparisons
                for comparison in comparisons:
                    #if the comparison is smaller than this experimentally chosen threshold
                    if comparison <= 0.55:
                        #get label from index of the comparison in comparisons list
                        label = comparisons.index(comparison)
                        #try to print the name of the person
                        try:
                            self.PrintText(frame, self.names[label], rect[0], rect[1])
                        #if it fails, the person doesn't exist anymore
                        except IndexError:
                            print("Person does not exist anymore, you have most likely forgotten to load files.")
                        #add a tupple which consists of blink information and label
                        labels.append(self.blink_detector(landmarks[i], label))
                #if there's no match, the face have to be unknown
                if all(i >= 0.55 for i in comparisons):
                    self.PrintText(frame, "unknown", rect[0], rect[1])
                    labels.append(None)


        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        # self.outputQ.put(frame)
        # cv2.imshow("SmartGate", image)
        # cv2.waitKey(1)
        return labels, frame