from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "user"
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  # senha hasheada
    role     = db.Column(db.String(20), default="client", nullable=False)

    cars     = db.relationship("Car", back_populates="owner", cascade="all, delete-orphan")
    questions = db.relationship("Question", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username!r} ({self.role})>"


class Car(db.Model):
    __tablename__ = "car"
    id         = db.Column(db.Integer, primary_key=True)
    owner_id   = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name       = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)

    owner       = db.relationship("User", back_populates="cars")
    sensor_data = db.relationship("SensorData", order_by="SensorData.id.desc()", back_populates="car", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Car {self.name!r} owner={self.owner_id}>"


class SensorData(db.Model):
    __tablename__ = "sensor_data"
    id          = db.Column(db.Integer, primary_key=True)
    time        = db.Column(db.String, nullable=False)
    temperature = db.Column(db.Float)
    humidity    = db.Column(db.Float)
    fire        = db.Column(db.Integer)
    colisao     = db.Column(db.Integer)
    rain        = db.Column(db.Integer)
    distance    = db.Column(db.Float)
    movement    = db.Column(db.Integer)
    car_id      = db.Column(db.Integer, db.ForeignKey("car.id"), nullable=False)

    car         = db.relationship("Car", back_populates="sensor_data")

    def __repr__(self):
        return f"<SensorData car_id={self.car_id} time={self.time}>"


class Question(db.Model):
    __tablename__ = "question"
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    question     = db.Column(db.Text, nullable=False)
    response     = db.Column(db.Text)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)

    user         = db.relationship("User", back_populates="questions")

    def __repr__(self):
        return f"<Question {self.id} user={self.user_id}>"
