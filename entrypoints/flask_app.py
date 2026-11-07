from flask import Flask, jsonify, request

import config
from app.domain import model
from app.adapters import orm
from app.service_layer import services, unit_of_work

# Tell SQLAlchemy how domain objects map to database tables.
orm.start_mappers()

app = Flask("entrypoints/flask_app.py")

# Define the API endpoint.
@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    client_request = request.get_json()

    try:
        # Create customer order line.
        order_line = model.OrderLine(
            order_id=client_request["order_id"],
            sku=client_request["sku"],
            qty=client_request["qty"]
        )

        # Allocate order line to a suitable batch.
        batch_ref = services.allocate(
            order_line=order_line,
            uow=unit_of_work.SQLAlchemyUnitOfWork()
        )

    except services.InvalidSku as e:
        return jsonify({"message": str(e)}), 400

    except model.OutOfStock as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"batch_ref": batch_ref}), 201