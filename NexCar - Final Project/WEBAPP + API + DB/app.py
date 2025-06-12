import os
import json
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, redirect, url_for
from api import api_bp
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt

from config import Config
from models import db, SensorData
from api import api_bp

# Inicializa Socket.IO (CORS aberto para todos os clientes)
socketio = SocketIO(cors_allowed_origins="*")

def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # Extensions
    db.init_app(app)
    with app.app_context():
        db.create_all()
    Migrate(app, db)
    JWTManager(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # integra Socket.IO
    socketio.init_app(app)

    # Register API blueprint
    app.register_blueprint(api_bp)

    # Rotas
    @app.route("/")
    def root():
        return redirect(url_for("landing_page"))

    @app.route("/landing")
    def landing_page():
        return render_template("landing.html")

    @app.get("/health")
    def health():
        return jsonify({"status": "NEXCAR API v1 online"})

    @app.route("/login")
    def login_page():
        return render_template("login.html")

    @app.route("/register")
    def register_page():
        return render_template("register.html")

    @app.route("/cliente_landing")
    def cliente_landing_page():
        return render_template("cliente_landing.html")

    @app.route("/minha_conta")
    def minha_conta_page():
        return render_template("minha_conta.html")

    @app.route("/admin_carros")
    def admin_carros_page():
        return render_template("admin_carros.html")

    @app.route("/carro/<int:car_id>")
    def carro_page(car_id):
        from models import Car
        car = Car.query.get_or_404(car_id)
        return render_template("dashboard_carro.html", car=car)

    return app

# Cria app
app = create_app()

# MQTT listener

def on_connect(client, userdata, flags, rc):
    print("Ligado ao broker MQTT (rc =", rc, ")")
    client.subscribe("sensor/dados")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        payload["time"] = datetime.utcnow().isoformat() + "Z"

        with app.app_context():
            row = SensorData(
                time=payload.get("time"),
                temperature=payload.get("temperature"),
                humidity=payload.get("humidity"),
                fire=payload.get("fire"),
                colisao=payload.get("colisao"),
                rain=payload.get("rain"),
                distance=payload.get("distance"),
                movement=payload.get("movement"),
                car_id=payload.get("car_id"),
            )
            db.session.add(row)
            db.session.commit()
            print("SensorData guardado (id =", row.id, ")")

            # Emite evento realtime
            socketio.emit("sensor_update", {
                "time": payload["time"],
                "temperature": payload.get("temperature"),
                "humidity": payload.get("humidity"),
                "fire": payload.get("fire"),
                "colisao": payload.get("colisao"),
                "rain": payload.get("rain"),
                "distance": payload.get("distance"),
                "movement": payload.get("movement"),
                "car_id": payload.get("car_id"),
            })
    except Exception as e:
        print("Erro ao processar mensagem MQTT:", e)


def start_mqtt():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("localhost", 1883, 60)
    client.loop_forever()

# Inicia MQTT apenas no processo principal
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
    threading.Thread(target=start_mqtt, daemon=True).start()

if __name__ == "__main__":
    # Executa via Socket.IO sem reloader
    socketio.run(
        app,
        #host="0.0.0.0",
        host="192.168.0.103",
        port=3000,
        debug=True,
        use_reloader=False
    )
