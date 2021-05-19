from flask import Flask, render_template, request, url_for
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
import numpy as np
from Helper import *
import os, shutil
import cv2

app=Flask(__name__)

@app.route('/')
def main():
    return render_template('index.html')

@app.route('/index/', methods=['GET', 'POST'])
def index():
    for filename in os.listdir('static/Output/'):
        os.remove('static/Output/'+filename)
        #print('Failed to delete %s. Reason: %s' % (file_path, e))
    img = request.files['image']

    img.save('static/Output/'+secure_filename(img.filename))
    img_dir = 'static/Output/' + secure_filename(img.filename)
    option = request.form['optradio']
    final = list()
    op = dFinal(option)
    if op >= 0.65:
        str1 = "The note is Genuine"
    else:
        str1 = "The note is Fake"
    final.append(str1)
    final.append(img_dir)
    return render_template('prediction.html', data = final)   

@app.route('/about/')
def about():
    return render_template('about.html') 

@app.route('/timeline/')
def timeline():
    return render_template('timeline.html')    

if __name__=='__main__':
    app.run(debug=True)   