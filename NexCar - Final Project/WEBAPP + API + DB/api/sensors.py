# api/sensors.py
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime

from . import api_bp
from models import db, Car, SensorData, User
from schemas import sensordata_schema, sensordata_schema_many

@api_bp.get("/cars/<int:car_id>/sensors")
@jwt_required()
def list_sensor(car_id):
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)

    # only clients (role=="client") get restricted to their own cars
    if user.role == "client":
        Car.query.filter_by(id=car_id, owner_id=uid).first_or_404()

    rows = (SensorData.query
                     .filter_by(car_id=car_id)
                     .order_by(SensorData.id.desc())
                     .all())
    return sensordata_schema_many.dump(rows), 200

@api_bp.get("/cars/<int:car_id>/sensors/latest")
@jwt_required()
def latest_sensor(car_id):
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)

    if user.role == "client":
        Car.query.filter_by(id=car_id, owner_id=uid).first_or_404()

    row = (SensorData.query
                    .filter_by(car_id=car_id)
                    .order_by(SensorData.id.desc())
                    .first())
    if not row:
        return {}, 204
    return sensordata_schema.dump(row), 200

@api_bp.post("/cars/<int:car_id>/sensors")
@jwt_required()
def post_sensor(car_id):
    uid  = int(get_jwt_identity())
    user = User.query.get_or_404(uid)

    # admin or iot can post to any; clients only to their own
    if user.role == "client":
        Car.query.filter_by(id=car_id, owner_id=uid).first_or_404()
    else:
        Car.query.get_or_404(car_id)

    data = request.get_json() or {}
    data.pop("car_id", None)
    data["time"] = datetime.utcnow().isoformat() + "Z"

    new_row = SensorData(car_id=car_id, **data)
    db.session.add(new_row)
    db.session.commit()
    return sensordata_schema.dump(new_row), 201
