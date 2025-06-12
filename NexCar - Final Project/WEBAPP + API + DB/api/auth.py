from flask import request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

from . import api_bp
from models import db, User
from schemas import user_schema

@api_bp.post("/auth/register")
def register():
    data = request.get_json()
    if User.query.filter_by(username=data["username"]).first():
        return {"msg": "Utilizador já existe"}, 400
    new_user = User(
        username=data["username"],
        password=generate_password_hash(data["password"]),
        role="client",
    )
    db.session.add(new_user)
    db.session.commit()
    return user_schema.dump(new_user), 201

@api_bp.post("/auth/login")
def login():
    data = request.get_json()
    user = User.query.filter_by(username=data["username"]).first()
    if not user or not check_password_hash(user.password, data["password"]):
        return {"msg": "Credenciais inválidas"}, 401

    # 👇  PASSA O ID PARA STRING
    token = create_access_token(identity=str(user.id))   # ← id como string
    return {"access_token": token}, 200


@api_bp.get("/me")
@jwt_required()
def me():
    uid  = get_jwt_identity()
    user = User.query.get(uid)
    return user_schema.dump(user), 200
