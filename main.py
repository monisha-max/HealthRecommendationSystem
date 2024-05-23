from flask import Flask, request, render_template, redirect, url_for, session
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
import boto3
from dotenv import load_dotenv
import os
import pandas as pd
from fuzzywuzzy import process, fuzz
import phonetics
from collections import defaultdict
from pymongo import MongoClient
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from skimage import filters
import requests 
from difflib import SequenceMatcher

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', b'\xeb\x8e,:\x9eP\xa6\xf1.\xb4\xa5\xf5\xb9f\xeag')
app.config["MONGO_URI"] = os.getenv('MONGO_URI')

mongo = PyMongo(app)
client = MongoClient('mongodb+srv://monishakollipara07:gkFrKz6IIlptSrI7@cluster0.oqf3fjt.mongodb.net/')
db = client['Cluster0']
collection = db['users']

bcrypt = Bcrypt(app)

textract_client = boto3.client(
    'textract',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION')
)

df = pd.read_csv('/Users/monishakollipara/Desktop/MLPROJECT/A_Z_medicines_dataset_of_India.csv')
medicine_names = df.iloc[:, 1].tolist()

#Creating a mapping from base names to full names and phonetic codes
medicine_name_map = defaultdict(list)
phonetic_map = {}
for full_name in medicine_names:
    base_name = full_name.split()[0].lower()
    medicine_name_map[base_name].append(full_name)
    phonetic_code = phonetics.dmetaphone(base_name)
    if phonetic_code[0]:
        phonetic_map[phonetic_code[0]] = full_name

merged_df = pd.read_csv('/Users/monishakollipara/Desktop/MLPROJECT/merged_df.csv')

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('upload_image'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = collection.find_one({'username': username})

        if user and bcrypt.check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('upload_image'))
        return 'Invalid username or password'

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username or not password:
            return 'Username and password are required'

        existing_user = collection.find_one({'username': username})

        if existing_user is None:
            hashpass = bcrypt.generate_password_hash(password).decode('utf-8')
            user_data = {
                'username': username,
                'password': hashpass,
                'transcriptions': []
            }
            collection.insert_one(user_data)
            session['username'] = username
            return redirect(url_for('upload_image'))

        return 'Username already exists'

    return render_template('register.html')

@app.route('/upload_image', methods=['GET', 'POST'])
def upload_image():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        image_file = request.files['image_file']
        content = image_file.read()

        #Debug
        print("File uploaded successfully")

        #Save 
        image_path = '/tmp/uploaded_image.png'
        try:
            with open(image_path, 'wb') as f:
                f.write(content)
        except Exception as e:
            print(f"Error saving the uploaded image: {e}")
            return "Error saving the uploaded image"

        #debug
        print("Image saved successfully")

        #preprocess the image
        try:
            image = Image.open(image_path)
            image = image.convert('L')  #convert to grayscale
            image = ImageEnhance.Contrast(image).enhance(2)  #enhance contrast
            image = image.filter(ImageFilter.MedianFilter())  #median filter
            image = image.point(lambda x: 0 if x < 140 else 255)  #Binarize
        except Exception as e:
            print(f"Error processing the image: {e}")
            return "Error processing the image"

        preprocessed_image_path = '/tmp/preprocessed_image.png'
        try:
            image.save(preprocessed_image_path)
        except Exception as e:
            print(f"Error saving the preprocessed image: {e}")
            return "Error saving the preprocessed image"

        #Debug
        print("Image preprocessed and saved successfully")

        #Using Tesseract OCR 
        try:
            tesseract_text = pytesseract.image_to_string(image)
        except Exception as e:
            print(f"Error using Tesseract OCR: {e}")
            return "Error using Tesseract OCR"

        #Debug
        print("Tesseract OCR results:", tesseract_text)

        #Calling Amazon Textract
        try:
            with open(preprocessed_image_path, 'rb') as image_file:
                content = image_file.read()
            response = textract_client.detect_document_text(Document={'Bytes': content})
        except Exception as e:
            print(f"Error calling Amazon Textract: {e}")
            return "Error calling Amazon Textract"

        print("Textract results:", response)

        extracted_texts = []
        for item in response['Blocks']:
            if item['BlockType'] == 'LINE':
                extracted_texts.append(item['Text'])

        #Combining Tesseract and Textract results
        combined_texts = list(set(extracted_texts + tesseract_text.splitlines()))

        #Logging the extracted texts
        print("Extracted Texts:", combined_texts)

        correct_medicines = set()
        for text in combined_texts:
            matching_full_names = find_closest_full_medicine_name(text, medicine_name_map, phonetic_map)
            if matching_full_names:
                correct_medicines.update(matching_full_names)

        session['results'] = list(correct_medicines)
        user = collection.find_one({'username': session['username']})
        if user:
            new_transcription = {'date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'), 'medicines': list(correct_medicines)}
            collection.update_one({'username': session['username']}, {'$push': {'transcriptions': new_transcription}})

        return redirect(url_for('results'))

    return render_template('upload.html')


@app.route('/results')
def results():
    if 'username' not in session:
        return redirect(url_for('login'))

    medicines = session.get('results', [])
    return render_template('results.html', medicines=medicines)

from urllib.parse import unquote, quote

@app.route('/details/<medicine_name>')
def details(medicine_name):
    if 'username' not in session:
        return redirect(url_for('login'))

    # Decode URL-encoded medicine name if necessary
    medicine_name = unquote(medicine_name).replace('__SLASH__', '/')
    print(f"Received medicine name: {medicine_name}") 
    medicine_details = get_medicine_details(medicine_name)

    if medicine_details is not None:
        substitutes = medicine_details[['substitute0', 'substitute1', 'substitute2', 'substitute3', 'substitute4']].values.flatten().tolist()
        substitute_urls = search_medicine_online(medicine_name, substitutes)
        return render_template('details.html', medicine_name=medicine_name, details=medicine_details.to_dict('records')[0], urls=substitute_urls)
    
    return 'No details found for this medicine', 404

@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = collection.find_one({'username': session['username']})
    if not user:
        return 'User not found', 404

    transcriptions = user.get('transcriptions', [])
    return render_template('profile.html', transcriptions=transcriptions)

def find_closest_full_medicine_name(text, name_map, phonetic_map, similarity_threshold=0.85):
    text = text.lower().strip()
    first_word = text.split()[0] if text.split() else text

    #Check if the first word is a single letter
    if len(first_word) == 1:
        return None

    #Direct matching with base names
    if first_word in name_map:
        return name_map[first_word]

    #Checking for matches with first 5 letters
    for base_name in name_map.keys():
        if first_word[:5] == base_name[:5]:
            return name_map[base_name]

    #Phonetic matching,dmetaphor
    text_phonetic = phonetics.dmetaphone(first_word)[0]
    if text_phonetic and text_phonetic in phonetic_map:
        return [phonetic_map[text_phonetic]]

    #Fuzzy matching with characters
    best_match = process.extractOne(text, name_map.keys(), scorer=fuzz.token_set_ratio, score_cutoff=85)
    if best_match:
        return name_map[best_match[0]]

    #Partial matching
    partial_matches = [name for name in name_map.keys() if fuzz.partial_ratio(text, name) > 85]
    if partial_matches:
        closest_partial_match = max(partial_matches, key=lambda name: fuzz.partial_ratio(text, name))
        return name_map[closest_partial_match]

    #Levenshtein distance matching
    closest_matches = sorted(name_map.keys(), key=lambda name: SequenceMatcher(None, text, name).ratio(), reverse=True)
    if closest_matches and SequenceMatcher(None, text, closest_matches[0]).ratio() > similarity_threshold:
        return name_map[closest_matches[0]]

    return None


def get_medicine_details(medicine_name):
    medicine_name = medicine_name.strip().lower()
    filtered_df = merged_df[merged_df['name'].str.strip().str.lower() == medicine_name]

    if filtered_df.empty:
        print(f"No details found for medicine: {medicine_name}")
        return None

    return filtered_df[['substitute0', 'substitute1', 'substitute2', 'substitute3', 'substitute4',
                        'sideEffect0', 'sideEffect1', 'sideEffect2', 'sideEffect3', 'Therapeutic Class', 'price(₹)', 'short_composition1', 'short_composition2']]

def search_medicine_online(medicine_name, substitutes):
    API_KEY = os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY')
    SEARCH_ENGINE_ID = os.getenv('GOOGLE_CUSTOM_SEARCH_ENGINE_ID')

    all_substitute_urls = {}

    for substitute_name in substitutes:
        if isinstance(substitute_name, str):
            search_query = substitute_name + ' buy online India'

            url = 'https://www.googleapis.com/customsearch/v1'
            params = {
                'q': search_query,
                'key': API_KEY,
                'cx': SEARCH_ENGINE_ID
            }

            response = requests.get(url, params=params)
            results = response.json()

            if 'items' in results and results['items']:
                all_substitute_urls[substitute_name] = results['items'][0]['link']
            else:
                print(f"No search results found for substitute: {substitute_name}")

    return all_substitute_urls

@app.route('/search', methods=['POST'])
def search():
    if 'username' not in session:
        return redirect(url_for('login'))

    medicine_name = request.form['medicine_name'].strip().lower()
    if not medicine_name:
        return 'Medicine name is required'
    matching_medicines = df[df['name'].str.lower().str.startswith(medicine_name)]
    if matching_medicines.empty:
        return 'No medicines found'

    matching_medicine_names = matching_medicines['name'].tolist()
    return render_template('search_results.html', medicines=matching_medicine_names)

from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'machinelearninggroupproject@gmail.com'
app.config['MAIL_PASSWORD'] = 'tfdj xdgy ulet vnuw'
app.config['MAIL_DEFAULT_SENDER'] = 'machinelearninggroupproject@gmail.com'

mail = Mail(app)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        feedback_text = request.form['feedback']
        username = session['username']

        msg = Message('Feedback from {}'.format(username),
                      recipients=['machinelearninggroupproject@gmail.com'])
        msg.body = feedback_text
        mail.send(msg)
        return 'Feedback sent successfully!'

    return render_template('feedback.html')

if __name__ == '__main__':
    app.run(debug=True)
