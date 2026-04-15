## Prerequisites
- Python 3.13.12 (tested only on this, not sure about further compatibility)
- A running PostgreSQL server (developed on version 18.3)
- Create a database and user, then configure connection details in .env

To build an exe:

Install pyinstaller: pip install -U pyinstaller

Run this command in the install directory: pyinstaller --onefile --noconsole main.py

