## Prerequisites
- Python 3.13.12 (tested only on this, not sure about further compatibility)
- A running PostgreSQL server (developed on version 18.3)
- Create a database and user, then configure connection details in .env
- .env.example is included, just edit .env.example and then rename it .env when done

To build an exe yourself:

Install pyinstaller: pip install -U pyinstaller

Run this command in the install directory: pyinstaller --onefile --noconsole -n FILENAME main.py

Make sure to have a .env file in the same directory as the .exe

