# NEXCAR: IoT Vehicle Monitoring System

This project outlines the design and implementation of NEXCAR, a real-time vehicle monitoring and control system that integrates physical sensors, actuators, a cloud-connected API, and multi-platform user interfaces.

The system was developed for the Integrated Telecommunications Project course of the Telecommunications and Informatics Engineering degree at the University of Minho.

## 👥 Authors
* José Pedro Ribeiro Novais (A105056)
* Miguel Freixo Machado (A103668)
* Tiago Rigueira Soares Diogo (A103665)

---

## 🎯 Objective
The system aims to increase vehicular safety and environmental awareness through the use of lightweight communication protocols (MQTT), REST APIs, and automation logic between sensors and actuators. Experimental validation demonstrates the system's reliability under various physical conditions.

---

## 🏗️ System Architecture
The NEXCAR system architecture was designed with a focus on modularity, scalability, and integration between physical sensors and front-end applications, both web and mobile. The system comprises three main functional blocks: data acquisition from sensors, processing and storage, and user interface.

### A. Data Acquisition and Publication
Data collection is performed by a set of real sensors that monitor environmental and vehicle movement variables, namely:
* Temperature - SHT3x
* Rain - YL-83 / FC-37
* Distance - HC-SR04
* Light - LDR
* Movement - PIR HC-SR501
* Flame - IR Flame Detector
* Accelerometer / Collision - MPU6050

The collected data is published to an MQTT broker (Mosquitto), which acts as a lightweight and efficient middleware for asynchronous, topic-based communication.

### B. MQTT Communication: Publish and Subscribe
The MQTT protocol intermediates communication between the sensors and the system's backend. Each sensor publishes its data to individual topics. Subscriber modules listen to all relevant topics using the `TOPIC_BASE/#` pattern. Data is temporarily stored, aggregated, and inserted into the `sensor_data.db` relational database for further processing.

### C. Processing, Storage, and Action
Data stored in the SQL database is analyzed by a decision code module, which interprets sensor values and takes automatic actions when critical conditions are detected. The system can activate the following actuators:
* Fan (when temperature exceeds a limit)
* Windshield Wipers (servo-motor, in case of rain detection)
* Sound Alarm (in case of collision danger)
* LED (activated by low light)

### D. User Interface
The system offers two main forms of user interaction:
1. A web application developed with the Flask framework and HTML, accessible via HTTP.
2. A mobile application developed in Kotlin, communicating via the REST API (Flask).

---

## 💻 System Features

### Web System
**Admin Dashboard**
* Real-time sensor data visualization and statistics.
* Real-time event visualization (collision, rain).
* User management: filter clients and remove cars.
* Customer support chat.
* Data comparison across all vehicles for statistical purposes.
* Data export (PDF or CSV).

**Client Dashboard**
* Personalized map showing exact location, real-time traffic, and nearby gas stations.
* Chat with admin.
* Real-time data and statistics visualization for registered vehicles.
* Real-time event visualization.
* Vehicle management (add/remove).
* Data export (PDF or CSV).

### Mobile System
**Admin Dashboard**
* Real-time sensor data visualization and statistics.
* Real-time event visualization.
* User management: filter clients and remove cars.

**Client Dashboard**
* Real-time data and statistics visualization.
* Real-time event visualization.
* Vehicle management (add/remove).
* Real-time alerts (notifications for events like collision or fire).

---

## 🧪 Tests and Results
Experimental tests validated the functionality of the sensors, dashboard integration, and actuators.

* **Sensors:** Tested for temperature variations, rain simulation, collision simulation, lighting scenarios, movement detection, distance measurement, and flame detection. The flame sensor showed false positives under direct sunlight, indicating a need for filters or calibration outdoors.
* **MQTT:** Tested with Mosquitto broker. Showed an average delivery latency of ~50 ms and a message loss rate of <1% for up to 20 simultaneous publishers (1 msg/sec).
* **System Capacity:** Supported up to 30 simultaneous clients with response times <200 ms. WebSocket (Socket.IO) performed well with multiple connections, allowing real-time dashboard updates without session conflicts.

---

## 🚀 Conclusion
NEXCAR demonstrates a modular and scalable architecture that is effective in both simulated and real tests. It features low latency, high reliability in MQTT communication, and solid integration between sensors, actuators, and applications. The developed web and mobile interfaces provide a comprehensive experience, reinforcing the practical utility of the system in intelligent vehicular monitoring contexts.

---
### 📄 Documentation
* [View the Full Project Report (PDF)](https://github.com/josenovais97/NEXCAR-Real-Time-IoT-Vehicle-Control-and-Monitoring-Platform/blob/main/NexCar%20-%20Final%20Project/RF-G1.pdf)
* [View the Project Poster (PDF)](https://github.com/josenovais97/NEXCAR-Real-Time-IoT-Vehicle-Control-and-Monitoring-Platform/blob/main/NexCar%20-%20Final%20Project/A2%20Poster.pdf)
