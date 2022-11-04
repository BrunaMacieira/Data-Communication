from flask import Flask
from bson.json_util import ObjectId
import json
from users import users
from simulation import simulation
from jobshop import jobshop


class MyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super(MyEncoder, self).default(obj)


app = Flask(__name__)
app.json_encoder = MyEncoder
app.register_blueprint(users)
app.register_blueprint(simulation)
app.register_blueprint(jobshop)
