# api/cars.py
from flask import request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity

from . import api_bp
from models import db, Car, User

@api_bp.get("/cars")
@jwt_required()
def list_cars():
    uid = int(get_jwt_identity())
    me = User.query.get_or_404(uid)

    if me.role == "admin":
        cars = Car.query.order_by(Car.created_at.desc()).all()
    else:
        cars = Car.query.filter_by(owner_id=uid).order_by(Car.created_at.desc()).all()

    # manually build payload so we include owner.username
    result = []
    for car in cars:
        result.append({
            "id": car.id,
            "name": car.name,
            "created_at": car.created_at.isoformat(),
            "owner": car.owner.username
        })
    return jsonify(result), 200

@api_bp.post("/cars")
@jwt_required()
def create_car():
    uid  = int(get_jwt_identity())
    name = request.json.get("name", "").strip() or abort(400, "Name required")
    new_car = Car(owner_id=uid, name=name)
    db.session.add(new_car)
    db.session.commit()
    return jsonify({
        "id": new_car.id,
        "name": new_car.name,
        "created_at": new_car.created_at.isoformat(),
        "owner": new_car.owner.username
    }), 201

@api_bp.route("/cars/<int:car_id>", methods=["DELETE"])
@jwt_required()
def delete_car(car_id):
    uid = int(get_jwt_identity())
    me  = User.query.get_or_404(uid)

    if me.role == "admin":
        car = Car.query.get_or_404(car_id)
    else:
        car = Car.query.filter_by(id=car_id, owner_id=uid).first_or_404()

    db.session.delete(car)
    db.session.commit()
    return "", 204
