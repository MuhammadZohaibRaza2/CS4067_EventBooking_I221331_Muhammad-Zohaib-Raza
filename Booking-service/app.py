from flask import Flask, request, jsonify
from pymongo import MongoClient
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Booking, Base
import pika
import json
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BookingService")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# RabbitMQ configuration
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))

def publish_booking_confirmation(booking_id: int, user_email: str):
    """Publish booking confirmation event to RabbitMQ"""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue='booking_confirmed')
        
        message = {
            "booking_id": booking_id,
            "user_email": user_email,
            "status": "CONFIRMED"
        }
        
        channel.basic_publish(
            exchange='',
            routing_key='booking_confirmed',
            body=json.dumps(message)
        )
        logger.info(f"Published booking confirmation for ID: {booking_id}")
        connection.close()
        
    except Exception as e:
        logger.error(f"Failed to publish message: {str(e)}")

@app.route('/bookings', methods=['POST'])
def create_booking():
    """Create a new booking and publish confirmation event"""
    data = request.get_json()
    logger.debug(f"Incoming request data: {data}")

    # Validate required fields
    required_fields = ["user_id", "event_id", "tickets", "amount", "user_email"]
    for field in required_fields:
        if field not in data:
            logger.error(f"Missing required field: {field}")
            return jsonify({"error": f"Missing required field: {field}"}), 400

    db = SessionLocal()
    try:
        # Create booking record
        booking = Booking(
            user_id=data["user_id"],
            event_id=data["event_id"],
            tickets=data["tickets"],
            amount=data["amount"],
            status="confirmed"
        )
        
        db.add(booking)
        db.commit()
        db.refresh(booking)
        logger.info(f"Booking created: ID {booking.id}")

        # Publish confirmation event
        publish_booking_confirmation(
            booking_id=booking.id,
            user_email=data["user_email"]
        )

        return jsonify({
            "id": booking.id,
            "user_id": booking.user_id,
            "event_id": booking.event_id,
            "tickets": booking.tickets,
            "amount": booking.amount,
            "status": booking.status
        }), 201

    except Exception as e:
        db.rollback()
        logger.error(f"Booking creation failed: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

    finally:
        db.close()

if __name__ == '__main__':
    app.run( port=5003)