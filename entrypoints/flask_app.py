from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import (
    Flask,
    jsonify,  # Converts Python data into an HTTP JSON response.
    request  # Give you access to the incoming request.
)

import config
from app.domain import model
from app.service_layer import services
from app.adapters import orm, repository

# This is where the ORM gets told how your domain objects 
# correspond to database tables.
orm.start_mappers()

engine = create_engine(config.get_postgres_uri())  # Creates the infrastructure that SQLAlchemy uses to communicate with the database.
get_session = sessionmaker(bind=engine)  # Creates a factory for database sessions.

app = Flask(__name__)  # Create a flask application


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    # Create a database session.
    session = get_session()

    # Create the sqlalchemy repository and fetch all batches in it.
    batches = repository.SqlAlchemyRepository(session).list()

    # Create an order line.
    order_line = model.OrderLine(
        order_id=request.json["order_id"],
        sku=request.json["sku"],
        qty=request.json["qty"]
    )

    if not services.is_valid_sku(order_line.sku, batches):
        return jsonify({"message": f"Invalid sku {order_line.sku}"}), 400

    try:
        # Allocate this order line against these batches.
        batch_ref = model.allocate(order_line, batches)
        
    except model.OutOfStock as e:
        return jsonify({"message": str(e)}), 400
    
    # Persist the allocation
    session.commit()

    # Return the HTTP response containing the allocated batch.
    return jsonify({"batch_ref": batch_ref}), 201