import json
import boto3
import pickle
import os
import urllib.parse
from datetime import datetime

# i wrote this lambda function to run my pipeline in AWS
# it gets triggered automatically when a file lands in S3
# same logic as my local pipeline.py but using AWS services

# connecting to AWS services i need
# boto3 is the Python library for AWS
# like how i use pdfplumber for PDFs
# boto3 is how Python talks to AWS
s3 = boto3.client('s3')
textract = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')

# same folder map as my local version
# maps document type to folder path in S3
FOLDER_MAP = {
    "Resume":   "hr/resumes/",
    "Invoice":  "finance/invoices/",
    "Paystub":  "finance/paystubs/",
    "Contract": "legal/contracts/",
    "Unknown":  "unknown/"
}

# same confidence threshold as local
# below 70% means model is not sure enough
CONFIDENCE_THRESHOLD = 70.0

# my organized bucket where sorted files go
# i hardcoded this because it never changes
ORGANIZED_BUCKET = "docsort-organized-nisha"

# keeping model loaded between invocations
# i learned that lambda reuses the same
# environment for multiple calls
# so loading model once saves time
model = None
vectorizer = None


def load_model():
    # loading my trained ml model
    # in lambda files are stored at /var/task/
    # i include model.pkl in my deployment package
    global model, vectorizer

    # if model already loaded dont load again
    # this is called caching - saves time
    if model is not None:
        print("model already loaded, skipping")
        return model, vectorizer

    try:
        model_path = "/var/task/model.pkl"
        vec_path   = "/var/task/vectorizer.pkl"

        with open(model_path, "rb") as f:
            model = pickle.load(f)

        with open(vec_path, "rb") as f:
            vectorizer = pickle.load(f)

        print("ml model loaded!")
        return model, vectorizer

    except Exception as e:
        print(f"couldnt load model: {e}")
        return None, None


def extract_text_from_s3(bucket, key):
    # extracting text from document
    # i use different approaches for different file types
    # textract for pdf and images
    # direct read for txt files

    file_ext = os.path.splitext(key)[1].lower()
    print(f"file type detected: {file_ext}")

    # txt files are simple - just read directly
    # no need for textract
    if file_ext == ".txt":
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            text = response['Body'].read().decode('utf-8')
            print(f"txt read directly: {len(text)} chars")
            return text
        except Exception as e:
            print(f"couldnt read txt: {e}")
            return None

    # pdf and images go through textract
    # textract is AWS version of pdfplumber
    # works natively with S3 so no download needed
    if file_ext in [".pdf", ".jpg", ".jpeg", ".png"]:
        try:
            response = textract.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': key
                    }
                }
            )

            # textract returns text in blocks
            # i only want LINE blocks not WORD blocks
            # LINE gives me complete sentences
            text = ""
            for block in response['Blocks']:
                if block['BlockType'] == 'LINE':
                    text += block['Text'] + " "

            print(f"textract got: {len(text)} chars")
            return text.strip()

        except Exception as e:
            print(f"textract failed: {e}")
            return None

    # anything else is unsupported
    print(f"unsupported file type: {file_ext}")
    return None


def classify_with_ml(text, model, vectorizer):
    # same classification as local classifier.py
    # tfidf converts text to numbers
    # logistic regression predicts document type
    # returns prediction and confidence score
    try:
        text_tfidf    = vectorizer.transform([text])
        prediction    = model.predict(text_tfidf)[0]
        probabilities = model.predict_proba(text_tfidf)[0]
        confidence    = max(probabilities) * 100
        print(f"ml predicted: {prediction} ({confidence:.1f}%)")
        return prediction, confidence

    except Exception as e:
        print(f"ml classification failed: {e}")
        return "Unknown", 0.0


def move_file_in_s3(source_bucket, source_key, doc_type):
    # moving file from intake to organized bucket
    # s3 doesnt have a real move operation
    # so i copy then delete - same result
    # learned this from AWS documentation

    filename = os.path.basename(source_key)
    folder   = FOLDER_MAP.get(doc_type, "unknown/")
    dest_key = folder + filename

    try:
        # copy file to organized bucket
        s3.copy_object(
            CopySource={
                'Bucket': source_bucket,
                'Key': source_key
            },
            Bucket=ORGANIZED_BUCKET,
            Key=dest_key
        )
        print(f"copied to: {dest_key}")

        # delete from intake bucket
        s3.delete_object(
            Bucket=source_bucket,
            Key=source_key
        )
        print("deleted from intake bucket")

        return dest_key

    except Exception as e:
        print(f"could not move file: {e}")
        return None


def log_to_dynamodb(filename, doc_type, confidence,
                    destination, time_taken, status):
    # saving result to dynamodb
    # like my local processing_log.txt but in cloud database
    # dynamodb is a simple key value store
    # i use filename as the unique key

    try:
        table = dynamodb.Table('docsort-logs')
        table.put_item(Item={
            'filename':      filename,
            'document_type': doc_type,
            'confidence':    str(round(confidence, 1)),
            'destination':   destination,
            'time_taken':    str(time_taken),
            'timestamp':     datetime.now().strftime(
                             "%Y-%m-%d %H:%M:%S"),
            'status':        status
        })
        print("logged to dynamodb!")

    except Exception as e:
        print(f"dynamodb logging failed: {e}")


def lambda_handler(event, context):
    # this is the main function lambda calls
    # every time a file lands in S3 this runs
    # event contains info about which file arrived

    start_time = datetime.now()
    print("lambda triggered!")

    # getting file info from the S3 event
    # AWS sends this automatically when file arrives
    record   = event['Records'][0]
    bucket   = record['s3']['bucket']['name']
    key      = urllib.parse.unquote_plus(
               record['s3']['object']['key'])
    filename = os.path.basename(key)

    print(f"new file: {filename}")
    print(f"bucket: {bucket}")

    # stage 1 - load ml model
    print("\nstage 1: loading model...")
    model, vectorizer = load_model()

    # stage 2 - extract text from document
    print("\nstage 2: extracting text...")
    text = extract_text_from_s3(bucket, key)

    # if we cant read the file send to unsupported
    if text is None or len(text.strip()) < 10:
        print("couldnt extract text - moving to unsupported")
        move_file_in_s3(bucket, key, "unsupported")
        log_to_dynamodb(
            filename, "Unsupported", 0,
            "unsupported/", 0, "unsupported"
        )
        return {
            'statusCode': 200,
            'body': 'file moved to unsupported folder'
        }

    # stage 3 - classify document type
    print("\nstage 3: classifying...")

    if model is None:
        # model failed to load
        # send to unknown folder
        doc_type   = "Unknown"
        confidence = 0.0
        print("no model available - marking as unknown")
    else:
        doc_type, confidence = classify_with_ml(
            text, model, vectorizer
        )

    # stage 4 - move file to correct folder in S3
    print(f"\nstage 4: moving to {doc_type} folder...")
    destination = move_file_in_s3(bucket, key, doc_type)

    # calculating how long it took
    end_time   = datetime.now()
    time_taken = round(
        (end_time - start_time).total_seconds(), 2
    )

    # stage 5 - log result to dynamodb
    print("\nstage 5: logging to dynamodb...")
    log_to_dynamodb(
        filename, doc_type, confidence,
        destination or "unknown",
        time_taken, "success"
    )

    print(f"\ndone! took {time_taken} seconds")

    # returning result
    return {
        'statusCode': 200,
        'body': json.dumps({
            'filename':      filename,
            'document_type': doc_type,
            'confidence':    round(confidence, 1),
            'destination':   destination,
            'time_taken':    time_taken,
            'status':        'success'
        })
    }