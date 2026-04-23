# RFID Door Access Project

This is a project I built to help manage access control for a shared space (like a makerspace or a workshop). It uses RFID tags and a Python backend to decide who is allowed to enter.

## My Motivation
I wanted to learn how to connect hardware (RFID readers) with a database and a message queue. This project helped me understand:
- How to use **Serial communication** in Python.
- How to store member data in a **SQL database**.
- How to sync data between a local server and a central one.

## Features
- **Local Database**: Stores access logs and member info so it works even if the internet is down.
- **RFID Scanning**: Connects to hardware readers to scan member cards.
- **Automated Logging**: Keeps track of every person who scans their card.
- **Simple Setup**: Can be run on a Raspberry Pi or a laptop.
- **Project Dashboard**: A web-based view to monitor access logs visually.

## Technology Used
- **Python**: The main programming language.
- **SQLite / SQLAlchemy**: For storing member credentials.
- **RabbitMQ**: For sending messages about scans.
- **PySerial**: To talk to the RFID reader hardware.

## How to use it
1. Copy the code to your machine.
2. Install the requirements: `pip install -r requirements.txt`.
3. Create your config file from the template: `cp config/template.ini config/mastercontrol.ini`.
4. Run the project: `python mastercontrol.py`.

## What I learned
This project taught me a lot about software architecture and how to handle real-world hardware events in Python. I also learned how to use the "Observable" pattern to make the code cleaner.
