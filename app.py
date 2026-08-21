from flask import Flask, request, jsonify, render_template, Response, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import uuid
import io
import csv
from datetime import datetime

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

class Attendee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    qr_token = db.Column(db.String(100), unique=True, nullable=False)
    checked_in = db.Column(db.Boolean, default=False)
    check_in_time = db.Column(db.DateTime, nullable=True)

with app.app_context():
    db.create_all()
    if Event.query.count() == 0:
        default_event = Event(name="Tech Con 2026", date="2026-06-01", capacity=50)
        db.session.add(default_event)
        db.session.commit()

def require_organizer():
    if request.headers.get('X-Role') != 'organizer':
        abort(403, description="Access Denied: Organizer role required.")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/events', methods=['GET'])
def get_events():
    events = Event.query.all()
    return jsonify([{"id": e.id, "name": e.name, "date": e.date, "capacity": e.capacity} for e in events]), 200

@app.route('/create_event', methods=['POST'])
def create_event():
    require_organizer()
    data = request.json
    new_event = Event(name=data['name'], date=data['date'], capacity=int(data['capacity']))
    db.session.add(new_event)
    db.session.commit()
    return jsonify({"success": "Event created!", "event_id": new_event.id}), 201

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    event = Event.query.get(data['event_id'])
    if not event: return jsonify({"error": "Event not found"}), 404
    
    if Attendee.query.filter_by(event_id=event.id).count() >= event.capacity:
        return jsonify({"error": "Event is at full capacity"}), 403

    new_token = str(uuid.uuid4())
    new_attendee = Attendee(event_id=event.id, qr_token=new_token)
    db.session.add(new_attendee)
    db.session.commit()
    return jsonify({"qr_token": new_token}), 201

@app.route('/scan', methods=['POST'])
def scan():
    require_organizer()
    data = request.json
    attendee = Attendee.query.filter_by(qr_token=data['qr_token']).first()
    
    if not attendee: return jsonify({"error": "Invalid token"}), 404
    if attendee.checked_in: return jsonify({"error": "Already checked in!"}), 409
        
    attendee.checked_in = True
    attendee.check_in_time = datetime.now()
    db.session.commit()
    return jsonify({"success": "Checked in successfully!"}), 200

@app.route('/live_stats/<int:event_id>', methods=['GET'])
def live_stats(event_id):
    event = Event.query.get(event_id)
    if not event: return jsonify({"error": "Event not found"}), 404
        
    return jsonify({
        "name": event.name,
        "capacity": event.capacity,
        "registered": Attendee.query.filter_by(event_id=event_id).count(),
        "checked_in": Attendee.query.filter_by(event_id=event_id, checked_in=True).count()
    })

@app.route('/export/<int:event_id>', methods=['GET'])
def export_csv(event_id):
    require_organizer()
    attendees = Attendee.query.filter_by(event_id=event_id).all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Token', 'Status', 'Check-in Time'])
    for a in attendees:
        cw.writerow([a.qr_token, "Present" if a.checked_in else "Absent", a.check_in_time.strftime("%Y-%m-%d %H:%M:%S") if a.check_in_time else "N/A"])
    return Response(si.getvalue(), mimetype='text/csv', headers={"Content-Disposition": f"attachment;filename=event_{event_id}_data.csv"})

if __name__ == '__main__':
    app.run(debug=True)