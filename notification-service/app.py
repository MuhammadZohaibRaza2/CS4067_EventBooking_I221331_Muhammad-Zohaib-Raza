import os
import pika
import json
from flask import Flask
from flask_mail import Mail, Message
from config.mongo import get_mongo_client
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Configure Flask-Mail for email notifications
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT"))
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = True
mail = Mail(app)

# MongoDB setup
mongo_client = get_mongo_client()
db = mongo_client[os.getenv("MONGO_DB")]
notifications_collection = db.notifications

def send_confirmation_email(booking_data):
    """Send email using Flask-Mail with proper app context"""
    with app.app_context():  # ✅ FIX: Ensure Flask app context is active
        try:
            msg = Message(
                subject="Booking Confirmation",
                sender=os.getenv("MAIL_USERNAME"),
                recipients=[booking_data["user_email"]],
                body=f"Dear User,\n\nYour booking {booking_data['booking_id']} is confirmed!\n\nBest Regards,\nYour Company"
            )
            mail.send(msg)
            
            # Log notification in MongoDB
            notifications_collection.insert_one({
                "booking_id": booking_data["booking_id"],
                "user_email": booking_data["user_email"],
                "status": "sent",
                "message": "Confirmation email sent successfully"
            })
            
            print(f"✅ Email sent successfully to {booking_data['user_email']}")
        except Exception as e:
            print(f"❌ Failed to send email: {str(e)}")
            notifications_collection.insert_one({
                "status": "failed",
                "error": str(e)
            })

def consume_booking_events():
    """RabbitMQ Consumer for booking confirmations"""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=os.getenv("RABBITMQ_HOST"),
                port=int(os.getenv("RABBITMQ_PORT"))
            )
        )
        channel = connection.channel()
        
        channel.queue_declare(queue='booking_confirmed')
        
        def callback(ch, method, properties, body):
            booking_data = json.loads(body)
            print(f"📩 Received booking confirmation: {booking_data}")
            send_confirmation_email(booking_data)  # ✅ Calls function with app context
        
        channel.basic_consume(
            queue='booking_confirmed',
            on_message_callback=callback,
            auto_ack=True
        )
        
        print("🚀 Waiting for booking confirmations...")
        channel.start_consuming()
    
    except Exception as e:
        print(f"❌ RabbitMQ connection error: {str(e)}")

if __name__ == "__main__":
    # Start RabbitMQ consumer in a separate thread
    import threading
    threading.Thread(target=consume_booking_events, daemon=True).start()
    
    # Start Flask app (optional endpoints)
    app.run(port=5003)
