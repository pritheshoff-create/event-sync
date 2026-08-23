from flask import Flask, request, jsonify, render_template, Response, session
from flask_sqlalchemy import SQLAlchemy

import uuid
import io
import csv
import os

from datetime import datetime


# ================================================================
# APP CONFIGURATION
# ================================================================

app = Flask(__name__)

# IMPORTANT:
# We are using a NEW database filename so your old events.db
# does not need to be deleted or modified.
#
# Flask-SQLAlchemy will normally place this inside:
#
# instance/eventos_new.db
#
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///eventos_new.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session secret.
#
# For a real deployment, put this in an environment variable.
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY",
    "eventos-development-secret-change-this"
)

# Demo organizer password.
#
# Change this if you want.
#
# For production, use an environment variable.
ORGANIZER_PASSWORD = os.environ.get(
    "ORGANIZER_PASSWORD",
    "admin123"
)


db = SQLAlchemy(app)


# ================================================================
# DATABASE MODELS
# ================================================================

class Event(db.Model):

    __tablename__ = "event"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(100),
        nullable=False
    )

    date = db.Column(
        db.String(50),
        nullable=False
    )

    capacity = db.Column(
        db.Integer,
        nullable=False
    )


class Attendee(db.Model):

    __tablename__ = "attendee"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("event.id"),
        nullable=False
    )

    qr_token = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    checked_in = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    check_in_time = db.Column(
        db.DateTime,
        nullable=True
    )


# ================================================================
# DATABASE INITIALIZATION
# ================================================================

with app.app_context():

    db.create_all()

    # Create a default event if the NEW database is empty.
    if Event.query.count() == 0:

        default_event = Event(
            name="Tech Con 2026",
            date="2026-06-01",
            capacity=50
        )

        db.session.add(default_event)

        db.session.commit()


# ================================================================
# AUTHENTICATION HELPER
# ================================================================

def organizer_required():

    return session.get("role") == "organizer"


def organizer_error():

    return jsonify({
        "error": "Organizer login required."
    }), 401


# ================================================================
# HOME
# ================================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# ================================================================
# ORGANIZER LOGIN
# ================================================================

@app.route(
    "/organizer_login",
    methods=["POST"]
)
def organizer_login():

    data = request.get_json(
        silent=True
    ) or {}

    password = data.get(
        "password"
    )

    if not password:

        return jsonify({
            "error": "Password is required."
        }), 400

    if password != ORGANIZER_PASSWORD:

        return jsonify({
            "error": "Invalid organizer password."
        }), 401

    # Store organizer status
    # inside Flask's signed session.

    session["role"] = "organizer"

    return jsonify({
        "success": "Organizer login successful."
    }), 200


# ================================================================
# ORGANIZER LOGOUT
# ================================================================

@app.route(
    "/organizer_logout",
    methods=["POST"]
)
def organizer_logout():

    session.clear()

    return jsonify({
        "success": "Logged out successfully."
    }), 200


# ================================================================
# CHECK LOGIN STATUS
# ================================================================

@app.route(
    "/organizer_status",
    methods=["GET"]
)
def organizer_status():

    return jsonify({
        "authenticated": organizer_required()
    }), 200


# ================================================================
# GET EVENTS
# ================================================================

@app.route(
    "/events",
    methods=["GET"]
)
def get_events():

    events = Event.query.order_by(
        Event.id.asc()
    ).all()

    return jsonify([
        {
            "id": event.id,
            "name": event.name,
            "date": event.date,
            "capacity": event.capacity
        }
        for event in events
    ]), 200


# ================================================================
# CREATE EVENT
# ================================================================

@app.route(
    "/create_event",
    methods=["POST"]
)
def create_event():

    # Only organizers can create events.

    if not organizer_required():

        return organizer_error()


    data = request.get_json(
        silent=True
    ) or {}


    name = data.get(
        "name"
    )

    date = data.get(
        "date"
    )

    capacity = data.get(
        "capacity"
    )


    # ------------------------------------------------------------
    # Validate name
    # ------------------------------------------------------------

    if not isinstance(
        name,
        str
    ) or not name.strip():

        return jsonify({
            "error": "Event name is required."
        }), 400


    name = name.strip()


    if len(name) > 100:

        return jsonify({
            "error":
                "Event name must be 100 characters or less."
        }), 400


    # ------------------------------------------------------------
    # Validate date
    # ------------------------------------------------------------

    if not isinstance(
        date,
        str
    ) or not date.strip():

        return jsonify({
            "error": "Event date is required."
        }), 400


    try:

        datetime.strptime(
            date,
            "%Y-%m-%d"
        )

    except ValueError:

        return jsonify({
            "error":
                "Date must use YYYY-MM-DD format."
        }), 400


    # ------------------------------------------------------------
    # Validate capacity
    # ------------------------------------------------------------

    try:

        capacity = int(
            capacity
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "error":
                "Capacity must be a valid number."
        }), 400


    if capacity <= 0:

        return jsonify({
            "error":
                "Capacity must be greater than zero."
        }), 400


    # ------------------------------------------------------------
    # Create event
    # ------------------------------------------------------------

    new_event = Event(
        name=name,
        date=date,
        capacity=capacity
    )


    try:

        db.session.add(
            new_event
        )

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "CREATE EVENT ERROR:",
            error
        )

        return jsonify({
            "error":
                "Failed to create event."
        }), 500


    return jsonify({
        "success":
            "Event created successfully.",

        "event_id":
            new_event.id

    }), 201


# ================================================================
# REGISTER ATTENDEE
# ================================================================

@app.route(
    "/register",
    methods=["POST"]
)
def register():

    # IMPORTANT:
    #
    # NO organizer authentication here.
    #
    # Attendees must be able to register publicly.

    data = request.get_json(
        silent=True
    ) or {}


    event_id = data.get(
        "event_id"
    )


    if event_id is None:

        return jsonify({
            "error":
                "Event ID is required."
        }), 400


    # Convert event ID to integer.

    try:

        event_id = int(
            event_id
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "error":
                "Invalid event ID."
        }), 400


    # ------------------------------------------------------------
    # Find event
    # ------------------------------------------------------------

    event = db.session.get(
        Event,
        event_id
    )


    if not event:

        return jsonify({
            "error":
                "Event not found."
        }), 404


    # ------------------------------------------------------------
    # Capacity
    # ------------------------------------------------------------

    registered_count = Attendee.query.filter_by(
        event_id=event.id
    ).count()


    if registered_count >= event.capacity:

        return jsonify({
            "error":
                "Event is at full capacity."
        }), 403


    # ------------------------------------------------------------
    # Create QR token
    # ------------------------------------------------------------

    new_token = str(
        uuid.uuid4()
    )


    new_attendee = Attendee(
        event_id=event.id,
        qr_token=new_token,
        checked_in=False
    )


    try:

        db.session.add(
            new_attendee
        )

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "REGISTRATION ERROR:",
            error
        )

        return jsonify({
            "error":
                "Registration failed."
        }), 500


    return jsonify({
        "qr_token":
            new_token
    }), 201


# ================================================================
# SCAN / CHECK IN
# ================================================================

@app.route(
    "/scan",
    methods=["POST"]
)
def scan():

    # Only organizers can scan tickets.

    if not organizer_required():

        return organizer_error()


    data = request.get_json(
        silent=True
    ) or {}


    qr_token = data.get(
        "qr_token"
    )

    event_id = data.get(
        "event_id"
    )


    # ------------------------------------------------------------
    # Validate token
    # ------------------------------------------------------------

    if not isinstance(
        qr_token,
        str
    ) or not qr_token.strip():

        return jsonify({
            "error":
                "QR token is required."
        }), 400


    # ------------------------------------------------------------
    # Validate event ID
    # ------------------------------------------------------------

    if event_id is None:

        return jsonify({
            "error":
                "Event ID is required."
        }), 400


    try:

        event_id = int(
            event_id
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "error":
                "Invalid event ID."
        }), 400


    # ------------------------------------------------------------
    # Make sure event exists
    # ------------------------------------------------------------

    event = db.session.get(
        Event,
        event_id
    )


    if not event:

        return jsonify({
            "error":
                "Event not found."
        }), 404


    # ------------------------------------------------------------
    # Find attendee belonging to THIS event
    # ------------------------------------------------------------

    attendee = Attendee.query.filter_by(
        qr_token=qr_token.strip(),
        event_id=event_id
    ).first()


    if not attendee:

        return jsonify({
            "error":
                "Invalid ticket for this event."
        }), 404


    # ------------------------------------------------------------
    # Prevent double check-in
    # ------------------------------------------------------------

    if attendee.checked_in:

        return jsonify({
            "error":
                "Already checked in!"
        }), 409


    # ------------------------------------------------------------
    # Check in attendee
    # ------------------------------------------------------------

    attendee.checked_in = True

    attendee.check_in_time = datetime.now()


    try:

        db.session.commit()

    except Exception as error:

        db.session.rollback()

        print(
            "CHECK-IN ERROR:",
            error
        )

        return jsonify({
            "error":
                "Failed to record check-in."
        }), 500


    return jsonify({
        "success":
            "Checked in successfully!"
    }), 200


# ================================================================
# LIVE STATISTICS
# ================================================================

@app.route(
    "/live_stats/<int:event_id>",
    methods=["GET"]
)
def live_stats(
    event_id
):

    # Organizer only.

    if not organizer_required():

        return organizer_error()


    event = db.session.get(
        Event,
        event_id
    )


    if not event:

        return jsonify({
            "error":
                "Event not found."
        }), 404


    registered = Attendee.query.filter_by(
        event_id=event_id
    ).count()


    checked_in = Attendee.query.filter_by(
        event_id=event_id,
        checked_in=True
    ).count()


    return jsonify({

        "name":
            event.name,

        "capacity":
            event.capacity,

        "registered":
            registered,

        "checked_in":
            checked_in

    }), 200


# ================================================================
# CSV EXPORT
# ================================================================

@app.route(
    "/export/<int:event_id>",
    methods=["GET"]
)
def export_csv(
    event_id
):

    # Organizer only.

    if not organizer_required():

        return organizer_error()


    event = db.session.get(
        Event,
        event_id
    )


    if not event:

        return jsonify({
            "error":
                "Event not found."
        }), 404


    attendees = Attendee.query.filter_by(
        event_id=event_id
    ).order_by(
        Attendee.id.asc()
    ).all()


    output = io.StringIO()


    writer = csv.writer(
        output
    )


    writer.writerow([
        "Token",
        "Status",
        "Check-in Time"
    ])


    for attendee in attendees:

        check_in_time = (

            attendee.check_in_time.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            if attendee.check_in_time

            else "N/A"
        )


        writer.writerow([

            attendee.qr_token,

            (
                "Present"
                if attendee.checked_in
                else "Absent"
            ),

            check_in_time

        ])


    filename = (
        f"event_{event_id}_data.csv"
    )


    return Response(

        output.getvalue(),

        mimetype="text/csv",

        headers={
            "Content-Disposition":
                f"attachment;filename={filename}"
        }

    )


# ================================================================
# RUN
# ================================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )