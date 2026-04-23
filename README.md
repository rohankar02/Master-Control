# 🔐 Smart Access Control: Industrial IoT Facility Management
### Full-Stack RFID Authentication & Decentralized Access Logging

This project implements a robust, production-ready access control system designed for high-availability facility management. It bridges the gap between hardware (RFID) and cloud infrastructure, featuring specialized logic for offline resilience and automated synchronization.

---

## 🎯 Engine Capabilities
- **Decentralized Architecture**: Features a local SQL-based caching layer that allows for continued operation and entry validation during network outages.
- **Hardware Integration**: High-performance serial communication interface (`PySerial`) for reliable real-time RFID polling.
- **Event-Driven Messaging**: Integrated **RabbitMQ** pipeline for asynchronous event logging and integration with downstream security monitoring services.
- **Entity Management**: Relational schema managed via **SQLAlchemy** for extensible user profiles and granular permission logic.

## 🛠️ Technical Architecture
- **Language**: Python 3.x
- **Database**: SQLite (Local Cache) | PostgreSQL (Central Node)
- **Middleware**: RabbitMQ (Message Broker)
- **Hardware Interface**: Serial / UART
- **Patterns**: Observable pattern for hardware events, Factory pattern for hardware drivers.

## 📈 Engineering Highlights
- **Reliability**: Implemented "Write-Ahead" logging for all access attempts, ensuring zero data loss during power cycles or connectivity drops.
- **Scalability**: Designed the system to be deployable across multiple entry points using a shared central database for unified management.
- **Security**: Sanitize all hardware inputs and utilize parameterize SQL queries to prevent injection attacks at the edge.

## 🚀 Getting Started
1. **Environment Setup**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Configuration**:
   ```bash
   cp config/template.ini config/access_config.ini
   # Edit access_config.ini with your SQL and RabbitMQ credentials
   ```
3. **Execution**:
   ```bash
   python main.py
   ```

---
*Developed by [Rohan Kar](https://github.com/rohankar02) as a demonstration of IoT Engineering and System Reliability.*
