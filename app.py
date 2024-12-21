from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime
from twilio.rest import Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Twilio configuration
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

# Database Model
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'company': self.company,
            'location': self.location,
            'message': self.message,
            'created_at': self.created_at.isoformat()
        }

def send_notification(contact):
    """Send SMS notification about new contact submission"""
    message_body = f"""
New Contact Form Submission:
Name: {contact.name}
Company: {contact.company}
Location: {contact.location}
Phone: {contact.phone}
Email: {contact.email}
Message: {contact.message[:100]}...
"""
    
    try:
        twilio_client.messages.create(
            body=message_body,
            from_=os.getenv('TWILIO_PHONE_NUMBER'),
            to=os.getenv('NOTIFICATION_PHONE')
        )
        return True
    except Exception as e:
        print(f"Error sending SMS: {str(e)}")
        return False

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/contact', methods=['POST'])
def submit_contact():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['name', 'email', 'phone', 'company', 'location', 'message']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Create new contact
        new_contact = Contact(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            company=data['company'],
            location=data['location'],
            message=data['message']
        )
        
        # Save to database
        db.session.add(new_contact)
        db.session.commit()
        
        # Send SMS notification
        send_notification(new_contact)
        
        return jsonify({
            'message': 'Contact form submitted successfully',
            'contact': new_contact.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    try:
        contacts = Contact.query.order_by(Contact.created_at.desc()).all()
        return jsonify({
            'contacts': [contact.to_dict() for contact in contacts]
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False)
