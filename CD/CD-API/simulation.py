from flask import Flask, request, jsonify, json
from db import get_database
from bson.json_util import ObjectId
import json
from flask import Blueprint
import jobshop
from users import token_required, admin_required
import pandas as pd

simulation = Blueprint('simulation', __name__)

db = get_database()


# Add simulation
# {
#     "author_id": "naewfiunfn3f023jf092"
#     "nr_operations": 3,
#     "nr_jobs": 3,
#     "nr_machines": 3,
#     "is_active": true,
#     "table": []
#     "production": []
# }
@simulation.post("/simulation")
@token_required
def add_simulation(f):
    if request.is_json:
        simulation_request = request.get_json()

        db.Simulation.insert_one(simulation_request)
        return jsonify(simulation_request), 201
    return {"error": "Request must be JSON"}, 415


# Find simulation by ObjectId (json)

# {
#     "_id": "62795f612acce938328b8f77"
# ⁄}
@simulation.get("/simulation")
@token_required
def find_simulation(f):
    if request.is_json:
        if len(request["_id"]) == 24:
            simulation_find = request.get_json()
            simulation_result = jsonify(db.Simulation.find_one({"_id": ObjectId(simulation_find["_id"])}))
            return simulation_result, 200
    return {"error": "Request must be JSON"}, 415


@simulation.get("/simulations")
@token_required
def list_simulations(f):
    simulations = db.Simulation.find()
    return jsonify(list(simulations)), 200


@simulation.delete("/simulation")
@token_required
def remove_simulation(f):
    if request.is_json:
        data = request.get_json()
        filter_id = {'_id': ObjectId(data["_id"])}
        new_values = {"$set": {"isActive": bool(False)}}
        update_result = db.Simulation.update_one(filter_id, new_values)
        if update_result.modified_count == 1:
            return {"msg": "Simulation removed successfully!"}, 200
        else:
            return {"error": "Not found"}, 404
    return {"error": "Request must be JSON"}, 415


# {
#     "_id": "8j298fifjweoifj",
#     "table": [
#         [[1, 3], [0, 2]]
#         [[0, 2], [1, 3]]
#     ]
# }
@simulation.put("/simulation")
@token_required
def update_data_simulation(f):
    if request.is_json:
        data = request.get_json()
        filter_id = {'_id': ObjectId(data["_id"])}
        table = data["table"]
        values = db.Simulation.find_one(filter_id)
        verify = False
        counter = 0
        for job in data["table"]:
            if job is not False:
                counter += 1
                if len(job) == values["nr_operations"]:
                    verify = True

        if values["nr_jobs"] != counter:
            return {"error": "All jobs should have at least one operation!"}, 400

        if not verify:
            return {"error": "At least one operation is empty!"}, 400

        production = jobshop.jobshop_resolver(table)
        update = {"$set": {"table": table, "production": production}}
        update_result = db.Simulation.update_one(filter_id, update)
        if update_result.modified_count == 1:
            return {"msg": "Table updated successfully!"}, 200

    return {"error": "Request must be JSON"}, 415


# {
#     "_id": "oenfowiehf43984f"
# }
@simulation.post("/simulationAutoExecute")
@token_required
def execute_auto_simulation(f):
    if request.is_json:
        simulation_find = request.get_json()
        simulation_element = db.Simulation.find_one({"_id": ObjectId(simulation_find["_id"])})

        for job in simulation_element["table"]:
            for i in range(len(job)):
                job[i] = tuple(job[i])
        result = jobshop.jobshop_resolver(simulation_element["table"])
        result = sorted(result, key=lambda d: d["task_id"])
        update = {"$set": {"production": result}}
        filter_id = {'_id': ObjectId(simulation_element["_id"])}
        update_result = db.Simulation.update_one(filter_id, update)

        return jsonify(result), 200

    return {"error": "Request must be JSON"}, 415


# {
#    "_id": "oenfowiehf43984f"   -> simulation ID to insert plan table
#    "production": [
#           {
#           "duration_time": 2,
#           "end_time": 2,
#           "job_id": 1,
#           "machine": 0,
#           "start_time": 0,
#           "task_id": 0
#           }
#     ]
# }
@simulation.put("/simulationManualUpdate")
def update_manual_simmulation(f):
    if request.is_json:
        simulation_insert = request.get_json()
        simulation_element = db.Simulation.find_one({"_id": ObjectId(simulation_insert["_id"])})
        if simulation_element is not None:
            conflict = False
            for production in simulation_insert["production"]:
                for operation in simulation_insert["production"]:
                    if production["job_id"] == operation["job_id"] and production["task_id"] == operation["task_id"] and production["duration_time"] == operation["duration_time"] and production["machine"] == operation["machine"] and production["start_time"] == operation["start_time"]:
                        continue
                    if operation["job_id"] == production["job_id"] and operation["end_time"] > production["start_time"]:
                        conflict = True
                        break

                    i1 = pd.Interval(operation["start_time"], operation["end_time"])
                    i2 = pd.Interval(production["start_time"], production["end_time"])

                    if production["machine"] == operation["machine"] and i1.overlaps(i2):
                        conflict = True
                        break

                    if conflict:
                        return {"Error": "Operation start and end time, overlaps other operation"}, 409
            table = simulation_element["production"]
            update = {"$set": {"production": table}}
            filter_id = {'_id': ObjectId(simulation_element["_id"])}
            update_result = db.Simulation.update_one(filter_id, update)
        return jsonify(update_result), 200
    return {"error": "Request must be JSON"}, 415
