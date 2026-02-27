from flask import Flask, request
from flask_bcrypt import Bcrypt
import globals
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

from blueprints.events.events import events_bp
from blueprints.bookings.bookings import bookings_bp
from blueprints.users.users import users_bp
from blueprints.auth.auth import auth_bp


app.register_blueprint(events_bp)
app.register_blueprint(bookings_bp)
app.register_blueprint(users_bp)
app.register_blueprint(auth_bp)

if __name__ == "__main__":
    app.run(debug=True)