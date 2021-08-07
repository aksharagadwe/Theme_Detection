import os
import io
import time
import s3fs
import json
import boto3
import pathlib
import requests
import tempfile

from flask import (Blueprint,
    render_template,
    Flask,request,
    session,
    redirect,
    url_for,
    
    send_file,abort)

from io import BytesIO 
from google.cloud import storage
from flask_session import Session
from werkzeug.utils import secure_filename
from werkzeug.datastructures import  FileStorage
from keras.preprocessing.sequence import pad_sequences




app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
Session(app)

S3_BUCKET     = "uploadedfilesfromtestui"
S3_KEY        = "AKIA2XRBHB6L6LIZA3DK"
S3_SECRET     = "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"
S3_LOCATION   = 'http://{}.s3.amazonaws.com/'.format(S3_BUCKET)



UPLOAD_URL = ""
CLOUD_STORAGE_BUCKET = ""


ALLOWED_EXTENSIONS = set(['wav','mp4','webm'])
 
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')




@app.route('/upload', methods=['POST'])
def upload():

    uploaded_file = request.files.get('uploaded-file')
    if uploaded_file and allowed_file(uploaded_file.filename):
        filename = secure_filename(uploaded_file.filename)


    uploaded_file.save(filename)
    

    bucket  = "uploadedfilesfromtestui"

    s3 = boto3.client(
        "s3",
        aws_access_key_id=S3_KEY,
        aws_secret_access_key=S3_SECRET
    )

    try:
        s3.upload_file(Filename=filename,Bucket=bucket,Key=filename)
    except ClientError as e:
        logging.error(e)

    transcribe = boto3.client('transcribe',aws_access_key_id=S3_KEY,
        aws_secret_access_key=S3_SECRET)
    job_name = filename.replace(".mp4","")+"transcription_job"
    job_uri = S3_LOCATION + filename
    transcribe.start_transcription_job(
    TranscriptionJobName=job_name,
    Media={'MediaFileUri': job_uri},
    MediaFormat='mp4',
    LanguageCode='en-US',
    OutputBucketName= "uploadedfilesfromtestui"
    )
    while True:
        status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
    time.sleep(5)
    pred=prediction(job_name)
    

    return pred[0]


def prediction(job_name):
    s3_res = boto3.resource(service_name='s3',aws_access_key_id=S3_KEY,
        aws_secret_access_key=S3_SECRET)
    obj = s3.Bucket('uploadedfilesfromtestui').Object(job_name).get()
    temp = json.loads(obj['Body'].read().decode('utf-8'))
    text = temp['results']['transcripts'][0]['transcript']


    s3f = s3fs.S3FileSystem(anon=False, key=S3_KEY, secret=S3_SECRET)
    model_file = h5py.File(s3f.open("s3://testmodelfornlp/model2.h5", "rb"))
    loaded_model = keras.models.load_model(f)
    with BytesIO() as data:
        s3_res.Bucket("testmodelfornlp").download_fileobj("tokenizer.pickle", data)
        data.seek(0)    # move back to the beginning after writing
        tokenizer = pickle.load(data)

    ex_seq = tokenizer.texts_to_sequences(text)
    ex_s_p = pad_sequences(ex_seq, maxlen=450)
    pred = loaded_model.predict(ex_s_p)

    return pred


    
if __name__ == '__main__':
    #app.run(ssl_context="adhoc")
    app.run(host='127.0.0.1', port=8080, debug=True)


