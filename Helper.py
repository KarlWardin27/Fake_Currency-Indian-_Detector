#!/usr/bin/env python
# coding: utf-8

# In[22]:


import cv2
import numpy as np
# import matplotlib.pyplot as plt
import os

#import anvil.media

#@anvil.server.callable
#def upload_image(file):
#    with anvil.media.TempFile(file) as filename:
#        _root=load(filename)

    # get file list from folder
notes = ['10','20','50','100', '200','500']
artio = [2.075723367, 2.212180173, 1.9959253487, 2.10026738, 2.1148898655, 2.16519103]
tolerance = [0.004586393, 0.006160723, 0.008263391, 0.024120747, 0.019034105, 0.020002683]
feature_set = [
    [0.2331274,0.0096001,0.2236,0.0644],
    [0.243820225,0.947776629,0.235955056,0.051706308],
    [0.08688764,0.097207859,0.120224719,0.257497415],
    [0.100482759,0.577044025,0.099827586,0.32468535],
    [0.401345291,0.167958656,0.293721973,0.069767442],
    [0.66313,0.7095218,0.1455,0.17838],
    [0.495689655,0.29009434,0.132758621,0.027122642],
    [0.18362069,0.543632075,0.735344828,0.037735849],
    [0.570786517,0.88262668,0.265168539,0.084281282],
]


feature_set_old = [
    [0.324112769, 0.385028302, 0.2039801, 0.2044009434],
    [0.247159451, 0.843353597, 0.161372756, 0.111560284],
    [0.055966209, 0.072921986, 0.173522703, 0.133981763],
    [0.067581837, 0.322695035, 0.1731151, 0.339148936],
    [0.610538543, 0.024822695, 0.299271383, 0.086119554],
    [0.648363252, 0.873353597, 0.173178458, 0.088652482]
]


feature_list = ['L_BRAILLE', 'R_BRAILLE', 'RBI_HI','RBI_EN', 'VALUE_STD', 'VALUE_HI', 'VALUE_HID', 'SEC_STRIP','EMBLEM']
feature_list_old = ['VALUE_CENTER', 'VALUE_RIGHT', 'VALUE_LEFT','RBI_EN_HI', 'EMBLEM','SEAL']
#-----------DATA SET ENDS-------------
detect_feat = [0, 1, 4, 5]
verify_feat = [2, 3, 6, 7, 8]

detect_feat_old = [0,1,2]
verify_feat_old = [3,4,5]

notes_type_old = ['10','20','50','100', 'Undetected']
notes_type = ['500','200','Undetected']

winner_old = [0,0,0,0,0]
winner = [0, 0, 0]
lead  = 0
feat_acc = np.zeros(detect_feat)
feat_acc_old = np.zeros(detect_feat_old)



def getFiles(_root):
    return next(os.walk(_root))[2]

# take image input
def takeImageInput(_root, _path):
    _path = _root + _path
    colored = cv2.imread(_path)
    _grayscale = cv2.cvtColor(colored, cv2.COLOR_BGR2GRAY)
    colored = cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
    return (colored, _grayscale)

# image preprocessing and noise reduction
def initialTransformations(_image):
    global thresh, blur, canny, filters
    _image = cv2.bilateralFilter(_image, 9, 50 ,50 )
    filters = _image
    _image = cv2.GaussianBlur(_image,(11,11) , 4)
    blur = _image
    _thresh = cv2.adaptiveThreshold(_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11,2 )
    canny = _thresh
    _thresh  = cv2.medianBlur(_thresh, 11)
    thresh = _thresh
    _image = _thresh
    # _image = cv2.Canny(_image,5,10)
    # canny = _image
    return _image

# returns set of points to be enclosed by bounding rectangle
def maxContour(_contour, imageArea):
    #global imageArea
    _pointList = np.array(_contour[0][:,0])
    _maxContourArea = 0
    for cnt in _contour:
        area = cv2.contourArea(cnt)
        if area/imageArea < 0.9:
            #print(imageArea)
            _pointList = np.append(_pointList, cnt[:,0], 0)
    return _pointList

def getFit(_image, box, clip=None):
    br = box[0]
    bl = box[1]
    tl = box[2]
    tr = box[3]

    _width = dist(br, bl)
    _height = dist(bl, tl)

    _pts1 = np.float32([br, bl, tl, tr])
    _pts2 = np.float32([[_width,_height],[0,_height], [0,0],[_width,0]])

    transformationMatrix = cv2.getPerspectiveTransform(_pts1, _pts2)
    transImage = cv2.warpPerspective(_image, transformationMatrix, (int(_width), int(_height)))
    if(clip!=None):
        transImage = transImage[clip[1]:int(_height)-clip[3], clip[0] : int(_width)-clip[2]]
    if(transImage.shape[0] > transImage.shape[1]):
        M = cv2.getRotationMatrix2D((transImage.shape[0]/2,transImage.shape[0]/2),-90,1)
        transImage = cv2.warpAffine(transImage,M,(transImage.shape[0],transImage.shape[1]))
    return transImage

def getFeatureImage(_fullImage, _feature):
    _height = _fullImage.shape[0]
    _width = _fullImage.shape[1]
    _x= int(_height * _feature[0])
    _y= int(_width *_feature[1])
    _dx = int(_height*_feature[2])
    _dy = int(_width*_feature[3])

    return _fullImage[_x:_x + _dx , _y : _y + _dy]


# match two images and generate descriptors
def imageMatcher(_standardImage, _sampleImage):
    _orb = cv2.ORB_create()
    try:
        _keyPoint_1, _descriptors_1 = _orb.detectAndCompute(_standardImage, None)
        _keyPoint_2, _descriptors_2 = _orb.detectAndCompute(_sampleImage, None)
        # In case there is no keypoint in sample image
        if len(_keyPoint_1) ==0  or len(_keyPoint_2) == 0:
            return (None,None)
        # Create a brute force matcher
        bruteForceMatcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        # Matches descriptors of images
        _matches = bruteForceMatcher.match(_descriptors_1, _descriptors_2)
        # sort matches wrt distance: less distance => more accurate match
        _matches = sorted(_matches, key=lambda x: x.distance)
        return (_matches, (_keyPoint_1, _keyPoint_2))
    except Exception as e:
        # print(e.args)
        return (None,(None, None))

# draw matches to a new image
def drawMatcher(_standardImage, _sampleImage, _keyPoints, _matches):
    result  = None
    _standardImage = cv2.cvtColor(_standardImage, cv2.COLOR_BGR2RGB)
    result = cv2.drawMatches(_standardImage,_keyPoints[0],_sampleImage,
    _keyPoints[1],_matches,result, flags=2)
    return result


# calculate confidence level for old
def calculateConfidence_old(confList):
    _threshold = np.array([65,65,65])
    #print(confList)
    if isOver(confList,65):
        dec = 'Fake'
        _result = 1 - _result 
    else:
        
        dec = 'Genuine'
        _result = (confList - 15)/ _threshold
        #print(confList)
        _result = 1 - _result
        _weight = np.array([0.6, 0.2 , 0.2])
        _result = _result * _weight
        _result = np.sum(_result)    

    return (_result, dec)

# confidence calculation for new notes
def calculateConfidence(confList):
    _threshold = np.array([65,65,65,65,65])
    #print(confList)
    if isOver(confList,65):
        
        dec = 'Fake'
        _result = 1 - _result 
    else:
        dec = 'Genuine'
        _result = (confList - 15)/ _threshold
        #print(_result)
        _result = 1 - _result
        _weight = np.array([0.30, 0.40 , 0.00, 0.05, 0.25])
        _result = _result * _weight
        _result = np.sum(_result)
    
    return (_result, dec)

def isOver(collection,_threshold):
    for i in collection:
        if i > _threshold:
            return True
        else:
            return False
            
    #return False


def dist(_x,_y):
    return ((_x[0] - _y[0])**2 + (_x[1]-_y[1])**2)**0.5


# detemines accuracy points on the matches
def determineAccuracy(_matches, _limit = None):
    if _limit == None or _limit == 0 :
        _limit = 3/2
    _sum = 0
    _limit = int(len(_matches)/_limit)
    for _ in _matches[:_limit]:
        _sum += _.distance
    _avg = float(0)
    try:
        _avg = _sum/_limit
    except Exception as e:
        # print(e.args)
        return int(65)
    return _avg

def verifyoldnotes(sample,reference_image,Note_Type,proper_image):
    add=0
    try:
        reference_image = cv2.cvtColor(reference_image, cv2.COLOR_BGR2RGB)
        matches , kp = imageMatcher(reference_image, sample)
        if matches == None or kp == None:
            # print('Feature ' + feature_list_old[d_feat] + ' failed.')
            pass
        accuracy = determineAccuracy(matches)
        if mini > accuracy:
            lead = i_note
            mini = accuracy
        mat_image = drawMatcher(reference_image, sample, kp, matches[0:20])
        mat_image = cv2.cvtColor(mat_image, cv2.COLOR_BGR2RGB)
        # title = str(d_feat) + " "  + notes_type_old[i_note]
        # cv2.namedWindow(title, cv2.WINDOW_KEEPRATIO)
        # cv2.imshow(title, mat_image)
        # print('Feature ' + feature_list_old[d_feat] + ' matches with accuracy  : ' + str(accuracy))
    except:
        pass
        # print('Error in feature ' + feature_list[d_feat] + ' of note ' + str(i)
    acMeasure = np.ones(len(verify_feat_old))
    for iter, feature_x in enumerate(verify_feat_old):
        sample = getFeatureImage(proper_image, feature_set_old[feature_x])
        reference_image = cv2.imread('D:/Code_Me/Python/Fake_Currency_Detector/Image/' + str(Note_Type)+'/000' + str(feature_x+1) + '.jpg', 0)
        try:
            matches , kp = imageMatcher(reference_image, sample)
            if matches == None or kp == None:
                #print('Feature ' + feature_list_old[feature_x] + ' not detected.')
                continue
            accuracy = determineAccuracy(matches)
            acMeasure[iter] = accuracy

            mat_image = drawMatcher(reference_image, sample, kp, matches[0:20])
            mat_image = cv2.cvtColor(mat_image, cv2.COLOR_BGR2RGB)
            resultant_image = mat_image
            title = str(iter)
            #cv2.namedWindow(title, cv2.WINDOW_KEEPRATIO)
            resultant_image = cv2.cvtColor(resultant_image, cv2.COLOR_BGR2RGB)
            #cv2.imshow(title, resultant_image)
            #print('Feature ' + feature_list_old[feature_x] + ' matches with distance value  : ' + str(accuracy))
        except:
            #print('Error in feature ' + feature_list_old[feature_x] + ' of note ' + str(i))
            pass
    add+=calculateConfidence_old(acMeasure)[0]    
    #print("Result : " + str(calculateConfidence_old(acMeasure)))
    #print(type(calculateConfidence(acMeasure)[0]))
    final=calculateConfidence_old(acMeasure)[0]
#     print(str(i) + ' - Note : ' + str(Note_Type))
#     if final>=0.65:
#         #print("the note is Genuine " + str(final))
#     else:
#         #print("the note is Fake " +str(final))
    #title = str(i)+ " " +  str(Note_Type) 
    #cv2.namedWindow(title, cv2.WINDOW_KEEPRATIO)
    proper_image = cv2.cvtColor(proper_image, cv2.COLOR_BGR2RGB)
    #cv2.imshow(title, proper_image)
    return final

def verifynewnotes( sample,reference_image,Note_Type,proper_image):
    add=0
    try:
        matches , kp = imageMatcher(reference_image, sample)
        if matches == None or kp == None:
            # print('Feature ' + feature_list[d_feat] + ' failed.')
            pass
        accuracy = determineAccuracy(matches)
        if mini > accuracy:
            lead = i_note
            mini = accuracy
        # mat_image = drawMatcher(reference_image, sample, kp, matches[0:20])
        # print('Feature ' + feature_list[d_feat] + ' matches with accuracy  : ' + str(accuracy))
    except:
        pass
        # print('Error in feature ' + feature_list[d_feat] + ' of note ' + str(i))

    acMeasure = np.ones(len(verify_feat))
    for iter, feature_x in enumerate(verify_feat):
        sample = getFeatureImage(proper_image, feature_set[feature_x])
        reference_image = cv2.imread('D:/Code_Me/Python/Fake_Currency_Detector/Image/' + str(Note_Type)+'/000' + str(feature_x+1) + '.jpg', 0)
        try:
            matches , kp = imageMatcher(reference_image, sample)
            if matches == None or kp == None:
                #print('Feature ' + feature_list[feature_x] + ' not detected.')
                acMeasure[iter] = 65
                continue
            accuracy = determineAccuracy(matches)
            acMeasure[iter] = accuracy

            mat_image = drawMatcher(reference_image, sample, kp, matches[0:20])
            resultant_image = cv2.cvtColor(resultant_image, cv2.COLOR_BGR2RGB)
            resultant_image = mat_image
            #title = str(iter)
            #cv2.namedWindow(title, cv2.WINDOW_KEEPRATIO)
            resultant_image = cv2.cvtColor(resultant_image, cv2.COLOR_BGR2RGB)
            #cv2.imshow(title, resultant_image)
            #print('Feature ' + feature_list[feature_x] + ' matches with distance value  : ' + str(accuracy))
        except:
            #print('Error in feature ' + feature_list[feature_x] + ' of note ' + str(i))
            pass
    add += calculateConfidence(acMeasure)[0]
    #print(str(i) + ' - Note : ' + str(Note_Type))
    #print("Result : " + str(calculateConfidence(acMeasure)))
    #print(type(calculateConfidence(acMeasure)[0]))
    final=calculateConfidence(acMeasure)[0]
#     if final>=0.65:
#         #print("the note is Genuine " + str(final))
#     else:
#         #print("the note is Fake " +str(final))
#     #print(str(i) + ' - Note : ' + str(Note_Type))
    #title = str(i)+ " " +  str(Note_Type) 
    #cv2.namedWindow(title, cv2.WINDOW_KEEPRATIO)
    proper_image = cv2.cvtColor(proper_image, cv2.COLOR_BGR2RGB)
    #cv2.imshow(title, proper_image)
    return final

def dFinal(option):
    # ----------STARTS---HERE------------------------#

    # -----ROOT - folder containing all the test note images-------------
    # -----Pass root to getFiles() to get list of files in that folder---
    #----------DATA SET STARTS------------


    root ="static/Output/"
    #root ="D:/Code_Me/Python/Fake_Currency_Detector/Image/training/20/"
    fileList = getFiles(root)
    fileList = sorted(fileList)
    Note_Type = int(option)

    megasum = float(0)
    for i in range(0,len(fileList)):
        path =  fileList[i]
        #Note_Type=int(input("Enter Which note you have to check '10','20','50','100, '500','200'"))
        #print(Note_Type)
        coloredImage, grayscale = takeImageInput(root, path)

        height = coloredImage.shape[0]
        width = coloredImage.shape[1]
        imageArea = float(height * width)

        # prepares image for contour detectection
        image = initialTransformations(grayscale)

        contours, hierarchy = cv2.findContours(image, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        # canvas = np.ones((height, width, 3))

        pointList = maxContour(contours, imageArea)
        rect = cv2.minAreaRect(pointList)
        rect = cv2.boxPoints(rect)
        rect = np.int0(rect)




        proper_image = getFit(coloredImage, rect)

        # cv2.namedWindow('title', cv2.WINDOW_KEEPRATIO)
        # proper_image = cv2.cvtColor(proper_image, cv2.COLOR_RGB2BGR)
        # canny = cv2.drawContours(thresh, [rect], 0, (0,0,0), 2)
        # cv2.imshow('title', canny)
        # cv2.waitKey(0)
        # exit()


    # ============ PROPER IMAGE TO PROCESS =================
        # referenceImage = cv2.imread('D:/Code_Me/Python/Fake_Currency_Detector/Image/500/0005.jpg',0)
        # sample = getFeatureImage(proper_image, feature_set[4])


    # ========================= TYPE DETECTION ================================================
        print(Note_Type)
        VUAP=0
        if Note_Type==200 or Note_Type==500:
                if Note_Type==200:
                    for x_out, d_feat in enumerate(detect_feat):
                        mini = 100
                        lead = 0
                        j=0
                        sample = getFeatureImage(proper_image, feature_set[d_feat])
                        reference_image = cv2.imread('D:/Code_Me/Python/Fake_Currency_Detector/Image/' + str(Note_Type)+'/000' + str(d_feat+1) + '.jpg', 0)
                        VUAP=verifynewnotes(sample,reference_image,Note_Type,proper_image)
                        #print(VUAP)
                
                elif Note_Type==500:
                    for x_out, d_feat in enumerate(detect_feat):
                        mini = 100
                        lead = 0
                        j=0
                        sample = getFeatureImage(proper_image, feature_set[d_feat])
                        reference_image = cv2.imread('D:/Code_Me/Python/Fake_Currency_Detector/Image/' + str(Note_Type)+'/000' + str(d_feat+1) + '.jpg', 0)
                        VUAP=verifynewnotes(sample,reference_image,Note_Type,proper_image)
                        #print(VUAP)

        else:
            if Note_Type==100 or Note_Type==50 or Note_Type==20 or Note_Type==10:

                if Note_Type==100:
                    for x_out, d_feat in enumerate(detect_feat_old):
                        mini = 100
                        lead = 0

                        sample = getFeatureImage(proper_image, feature_set_old[d_feat])
                        reference_image = cv2.imread('D:/Code_Me/Python/Fake_Currency_Detector/Image/' + str(Note_Type)+'/000' + str(d_feat+1) + '.jpg', 0)
                        VUAP=verifyoldnotes(sample,reference_image,Note_Type,proper_image)
                        #print(VUAP)

                elif Note_Type==50:
                    for x_out, d_feat in enumerate(detect_feat_old):
                        mini = 100
                        lead = 0
                        sample = getFeatureImage(proper_image, feature_set_old[d_feat])
                        reference_image = cv2.imread('D:/Code_Me/Python/Fake_Currency_Detector/Image/' + str(Note_Type)+'/000' + str(d_feat+1) + '.jpg', 0)
                        VUAP=verifyoldnotes(sample,reference_image,Note_Type,proper_image)
                        #print(VUAP)

                elif Note_Type==20:
                    for x_out, d_feat in enumerate(detect_feat_old):
                        mini = 100
                        lead = 0
                        sample = getFeatureImage(proper_image, feature_set_old[d_feat])
                        reference_image = cv2.imread('D:/Code_Me/Python/Fake_Currency_Detector/Image/' + str(Note_Type)+'/000' + str(d_feat+1) + '.jpg', 0)
                        VUAP=verifyoldnotes(sample,reference_image,Note_Type,proper_image)
                        #print(VUAP)
            
                elif Note_Type==10:
                    for x_out, d_feat in enumerate(detect_feat_old):
                        mini = 100
                        lead = 0
                        sample = getFeatureImage(proper_image, feature_set_old[d_feat])
                        reference_image = cv2.imread('D:/Code_Me/Python/Fake_Currency_Detector/Image/' + str(Note_Type)+'/000' + str(d_feat+1) + '.jpg', 0)
                        VUAP=verifyoldnotes(sample,reference_image,Note_Type,proper_image)
                        #print(VUAP)
        print(VUAP)
        return VUAP