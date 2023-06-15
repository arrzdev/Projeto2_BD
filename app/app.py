#!/usr/bin/python3
import os
from logging.config import dictConfig

import psycopg
from flask import flash
from flask import Flask
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from psycopg.rows import namedtuple_row
from psycopg_pool import ConnectionPool

from random import randint


# postgres://{user}:{password}@{hostname}:{port}/{database-name}
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://postgres:postgres@postgres/postgres")
FETCH_ONE = "one"
FETCH_ALL = "all"
INSERT = "insert"

pool = ConnectionPool(conninfo=DATABASE_URL)
# the pool starts connecting immediately.

dictConfig(
  {
    "version": 1,
    "formatters": {
      "default": {
        "format": "[%(asctime)s] %(levelname)s in %(module)s:%(lineno)s - %(funcName)20s(): %(message)s",
      }
    },
    "handlers": {
      "wsgi": {
        "class": "logging.StreamHandler",
        "stream": "ext://flask.logging.wsgi_errors_stream",
        "formatter": "default",
      }
    },
    "root": {"level": "INFO", "handlers": ["wsgi"]},
  }
)

app = Flask(__name__)
log = app.logger

def execute_query(query, args=(), action=INSERT):
  '''
  Execute a query and return the result.
  '''
  result = True
  try:
    with pool.connection() as conn:
      with conn.cursor(row_factory=namedtuple_row) as cur:
        cur.execute(query, args)
        if action != INSERT:
          result = cur.fetchall() if action == FETCH_ALL else cur.fetchone()
  except:
    log.exception("Error executing query: %s", query)
    result = False

  return result


@app.route("/", methods=["GET"])
def index():
  return render_template("index.html")

@app.route("/customers", methods=["GET"])
def customer_index():
  #get filter arg from request
  name_q = request.args.get("q")

  if name_q is None or name_q == "":
    #run query without filter
    query = "SELECT * FROM customer"
    args = ()
  else:
    query = "SELECT * FROM customer WHERE name ILIKE %s"
    args = (name_q, )

  customers = execute_query(query, args, action=FETCH_ALL)
  return render_template(
    "/customers/index.html",
    navbar_text="Customers", 
    current_q=name_q,
    customers=customers
  )

@app.route("/customers/<int:customer_id>", methods=["GET"])
def customer_show(customer_id):
  customer = execute_query(
    "SELECT * FROM customer WHERE customer_id = %s",
    (customer_id, ),
    action=FETCH_ONE
  )
  return jsonify(customer)

@app.route("/customers/add", methods=["GET"])
def customer_add():
  #/customers/add?name=joana&email=joana@wtf.pt&phone=969696969&adress=Manhica
  cust_no = randint(0, 999999)
  name = request.args.get("name", "debug")
  email = request.args.get("email", f"debug-{cust_no}@tecnico.ulisboa.pt")
  phone = request.args.get("phone", "969696969")
  address = request.args.get("address", "Taguspark")

  # if name is None or email is None or phone is None or address is None:
  #   flash("Please fill out all fields")

  #create query
  query = "INSERT INTO customer (cust_no, name, email, phone, address) VALUES (%s, %s, %s, %s, %s)"
  args = (cust_no, name, email, phone, address)

  #insert customer into db
  sucessfull = execute_query(query, args, action=INSERT)
  # if not sucessfull:
  #   flash("Error inserting customer")
  
  #render main_page
  return redirect(url_for("customer_index"))

@app.route("/ping", methods=("GET",))
def ping():
  log.debug("ping!")
  return jsonify({"message": "pong!", "status": "success"})


if __name__ == "__main__":
  app.run()
