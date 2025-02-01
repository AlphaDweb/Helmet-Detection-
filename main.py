from flask import Flask, request, render_template, send_file, url_for
from flask_mail import Mail, Message
import random
import string
import torch
import cv2
import numpy as np
import os

# Initialize app
app = Flask(__name__)

# Flask-Mail setup
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465  # SSL port
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'user email'  # Your Gmail address
app.config['MAIL_PASSWORD'] = 'user app password or password '  # Your Gmail app password
app.config['MAIL_DEFAULT_SENDER'] = 'default sender email'  # Same as above
mail = Mail(app)

# Load YOLO model
model = torch.hub.load('ultralytics/yolov5', 'custom', path='best.pt', _verbose=False)

# Define directories to save images and receipts
IMG_DIR = os.path.join('static', 'results')
RECEIPT_DIR = os.path.join('static', 'receipts')

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(RECEIPT_DIR, exist_ok=True)

# Default route for homepage
@app.route('/')
def home():
    return render_template('index.html')

# Prediction route
@app.route('/predict', methods=['POST'])
def predict():
    # Check if the file exists
    if 'file' not in request.files:
        return "No file uploaded", 400

    file = request.files['file']

    # Validate file type
    if file.filename == '':
        return "No selected file", 400

    # Read and decode the image
    bytes = np.fromfile(file, np.uint8)
    img_array = cv2.imdecode(bytes, cv2.IMREAD_COLOR)

    # Perform inference
    result = model(img_array)
    labels = result.pandas().xyxy[0]['name'].tolist()  # Extract detected labels

    # Save detection result
    filename = os.path.join(IMG_DIR, file.filename)
    cv2.imwrite(filename, result.render()[0])

    # Check if helmet is detected
    if 'helmet' not in labels:  # Assuming 'helmet' is the model label
        # Generate fine receipt
        receipt_name = generate_fine_receipt(file.filename)
        return render_template(
            "index.html", 
            image=filename, 
            receipt=url_for('download_receipt', filename=receipt_name)
        )

    # Render the result without a fine
    return render_template("index.html", image=filename)

# Function to generate fine receipt
def generate_fine_receipt(filename):
    # Generate a random name for the violator
    violator_name = f"{random.choice(['John', 'Jane', 'Alex', 'Chris'])} {random.choice(['Doe', 'Smith', 'Taylor'])}"
    fine_amount = 10000  # Fixed fine amount
    receipt_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))  # Random ID

    # Create the receipt text
    receipt_content = f"""
    ----------------------------------------
                    Fine Receipt
    ----------------------------------------
    Receipt ID: {receipt_id}
    Violator: {violator_name}
    Violation: No Helmet Detected
    Fine Amount: ₹{fine_amount}
    ----------------------------------------
    Thank you for following safety rules.
    ----------------------------------------
    """

    # Save the receipt as a text file with UTF-8 encoding
    receipt_name = f"receipt_{receipt_id}.txt"
    receipt_path = os.path.join(RECEIPT_DIR, receipt_name)
    with open(receipt_path, 'w', encoding='utf-8') as file:
        file.write(receipt_content)

    return receipt_name

# Route to download receipt
@app.route('/receipt/<filename>')
def download_receipt(filename):
    path = os.path.join(RECEIPT_DIR, filename)
    return send_file(path, as_attachment=True)

# Route to send email with fine receipt
@app.route('/send_email', methods=['POST'])
def send_email():
    email = request.form.get('email')
    receipt_name = request.form.get('receipt_name')
    receipt_path = os.path.join(RECEIPT_DIR, receipt_name)

    if not email:
        return "Email address is required", 400

    # Create email message
    msg = Message("Fine Slip Generated", recipients=[email])
    msg.body = "Dear violator, \n\nPlease find attached your fine slip for the helmet violation. \n\nThank you."
    with app.open_resource(receipt_path) as fp:
        msg.attach(receipt_name, 'text/plain', fp.read())

    # Send email
    try:
        mail.send(msg)
        return render_template('index.html', success_message="Fine slip sent to the violator's email!")
    except Exception as e:
        return f"Error sending email: {e}"

# Run app
if __name__ == '__main__':
    app.run(debug=True, port=5000)
