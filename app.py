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
    if not data or not data.get('name') or not data.get('capacity'):
        return jsonify({"error": "Missing event name or capacity"}), 400
    
    new_event = Event(
        name=data['name'], 
        date=data.get('date', datetime.now().strftime('%Y-%m-%d')), 
        capacity=int(data['capacity'])
    )
    db.session.add(new_event)
    db.session.commit()
    return jsonify({"success": "Event created successfully!", "event_id": new_event.id}), 201

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('event_id'):
        return jsonify({"error": "Event ID required"}), 400

    event = Event.query.get(data['event_id'])
    if not event: 
        return jsonify({"error": "Event not found"}), 404
    
    current_registrations = Attendee.query.filter_by(event_id=event.id).count()
    if current_registrations >= event.capacity:
        return jsonify({"error": "Event is at full capacity!"}), 403

    new_token = str(uuid.uuid4())
    new_attendee = Attendee(event_id=event.id, qr_token=new_token)
    db.session.add(new_attendee)
    db.session.commit()
    return jsonify({"qr_token": new_token}), 201

@app.route('/scan', methods=['POST'])
def scan():
    require_organizer()
    data = request.json
    if not data or not data.get('qr_token'):
        return jsonify({"error": "QR token required"}), 400

    attendee = Attendee.query.filter_by(qr_token=data['qr_token']).first()
    
    if not attendee: 
        return jsonify({"error": "Invalid token or attendee not found"}), 404
    if attendee.checked_in: 
        return jsonify({"error": "Attendee already checked in!"}), 409
        
    attendee.checked_in = True
    attendee.check_in_time = datetime.now()
    db.session.commit()
    return jsonify({"success": "Checked in successfully!"}), 200

@app.route('/live_stats/<int:event_id>', methods=['GET'])
def live_stats(event_id):
    event = Event.query.get(event_id)
    if not event: 
        return jsonify({"error": "Event not found"}), 404
        
    registered_count = Attendee.query.filter_by(event_id=event_id).count()
    checked_in_count = Attendee.query.filter_by(event_id=event_id, checked_in=True).count()

    return jsonify({
        "name": event.name,
        "capacity": event.capacity,
        "registered": registered_count,
        "checked_in": checked_in_count
    }), 200

@app.route('/ai_insights/<int:event_id>', methods=['GET'])
def ai_insights(event_id):
    require_organizer()
    event = Event.query.get(event_id)
    if not event: 
        return jsonify({"error": "Event not found"}), 404
    
    reg_count = Attendee.query.filter_by(event_id=event_id).count()
    check_count = Attendee.query.filter_by(event_id=event_id, checked_in=True).count()
    utilization = round((reg_count / event.capacity) * 100) if event.capacity > 0 else 0
    check_rate = round((check_count / reg_count) * 100) if reg_count > 0 else 0
    
    analysis = f"**Arrival Telemetry Analysis:** Currently, {check_rate}% of registered participants have checked into the venue. Overall venue capacity utilization sits at {utilization}%.\n\n**Strategic Recommendation:** Send a push reminder notification to the {reg_count - check_count} pending attendees to optimize entry throughput."
    
    return jsonify({"analysis": analysis}), 200

@app.route('/export/<int:event_id>', methods=['GET'])
def export_csv(event_id):
    require_organizer()
    attendees = Attendee.query.filter_by(event_id=event_id).all()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Token', 'Status', 'Check-in Time'])
    for a in attendees:
        cw.writerow([
            a.qr_token, 
            "Present" if a.checked_in else "Absent", 
            a.check_in_time.strftime("%Y-%m-%d %H:%M:%S") if a.check_in_time else "N/A"
        ])
    return Response(
        si.getvalue(), 
        mimetype='text/csv', 
        headers={"Content-Disposition": f"attachment;filename=event_{event_id}_report.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True)