from flask import Flask
dbtour_app = Flask(__name__)
from bgWebsite import routes

dbtour_app.secret_key = "emphasis"
