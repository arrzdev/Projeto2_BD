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
INSERT_REMOVE = "insert"

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

def execute_query(query, args=(), action=INSERT_REMOVE):
  '''
  Execute a query and return the result.
  '''
  result = True
  try:
    with pool.connection() as conn:
      with conn.cursor(row_factory=namedtuple_row) as cur:
        cur.execute(query, args)
        if action != INSERT_REMOVE:
          result = cur.fetchall() if action == FETCH_ALL else cur.fetchone()
  except:
    log.exception("Error executing query: %s", query)
    result = False

  return result


@app.route("/", methods=["GET"])
def index():
  #render customers page by default
  return redirect(url_for("customers_index"))


########################################################

@app.route("/customers", methods=["GET"])
def customers_index():
  #get filter arg from request
  name_q = request.args.get("q", "")
  page = int(request.args.get("page", 1))

  if name_q == "":
    #run query without filter
    query = "SELECT * FROM customer"
    args = ()
  else:
    query = "SELECT * FROM customer WHERE name ILIKE %s"
    args = (name_q, )

  customers = execute_query(query, args, action=FETCH_ALL)

  #display 8 customers per page
  max_page = (len(customers) // 8)
  if len(customers) % 8 != 0:
    max_page += 1
  customers = customers[(page-1)*8:page*8]

  return render_template(
    "/customers/index.html",
    navbar_text="Customers", 
    current_q=name_q,
    current_page=page,
    max_page=max_page,
    search_label="Search by name..",
    customers=customers
  )

# ADD CUSTOMER
@app.route("/customers/add", methods=["GET"])
def customers_add():
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
  sucessfull = execute_query(query, args, action=INSERT_REMOVE)
  # if not sucessfull:
  #   flash("Error inserting customer")
  
  #render main_page
  return redirect(url_for("customers_index"))

# REMOVE CUSTOMER
@app.route("/customers/delete", methods=["GET"])
def customers_remove():
  delete_all = int(request.args.get("all", 0))
  customer_ids = request.args.get("ids", "")

  # if customer_ids is False and customer_ids == []:
  #   flash("Please select a customer to remove")
  #   return redirect(url_for("customers_index"))

  #if delete_all is true, delete all customers
  if delete_all == 1:
    query = "DELETE FROM customer"
    args = ()
  else:
    #parse ids
    customer_ids = tuple(map(int, customer_ids.split(",")))
    placeholders = ", ".join(["%s"] * len(customer_ids))

    query = f"DELETE FROM customer WHERE cust_no IN ({placeholders})"
    args = customer_ids

  #execute query
  sucessfull = execute_query(query, args, action=INSERT_REMOVE)

  # if not sucessfull:
  #   flash("Error deleting customer(s)")
  
  #render main_page
  return redirect(url_for("customers_index"))

########################################################

@app.route("/products", methods=["GET"])
def products_index():
  #get filter arg from request
  name_q = request.args.get("q", "") #sku / name
  page = int(request.args.get("page", 1))

  if name_q == "":
    #run query without filter
    query = "SELECT * FROM product"
    args = ()
  else:
    query = "SELECT * FROM product WHERE name ILIKE %s OR sku ILIKE %s"
    args = (name_q, name_q)

  products = execute_query(query, args, action=FETCH_ALL)

  #display 8 products per page
  max_page = (len(products) // 8)
  if len(products) % 8 != 0:
    max_page += 1
  products = products[(page-1)*8:page*8]

  return render_template(
    "/products/index.html",
    navbar_text="Products", 
    current_q=name_q,
    current_page=page,
    max_page=max_page,
    search_label="Search by name or sku..",
    products=products
  )


# ADD PRODUCT
@app.route("/products/add", methods=["GET"])
def products_add():
  random_no = randint(0, 999999)
  sku = request.args.get("sku", f"d-{random_no}")
  name = request.args.get("name", f"n-{random_no}")
  description = request.args.get("description", "debug")
  price = request.args.get("price", 0)
  ean = request.args.get("ean", random_no)

  # if sku is None or name is None or description is None or price is None or ean is None:
    # flash("Please fill out all fields")

  #create query
  query = "INSERT INTO product (sku, name, description, price, ean) VALUES (%s, %s, %s, %s, %s)"
  args = (sku, name, description, price, ean)

  #insert customer into db
  sucessfull = execute_query(query, args, action=INSERT_REMOVE)
  # if not sucessfull:
  #   flash("Error inserting customer")
  
  #render main_page
  return redirect(url_for("products_index"))

# REMOVE CUSTOMER
@app.route("/products/delete", methods=["GET"])
def products_remove():
  delete_all = int(request.args.get("all", 0))
  product_ids = request.args.get("ids", "")

  # if product_ids == "":
  #   flash("Please select a product to remove")
  #   return redirect(url_for("products_index"))

  #if delete_all is true, delete all customers
  if delete_all == 1:
    query = "DELETE FROM product"
    args = ()
  else:
    #parse ids
    product_ids = tuple(product_ids.split(","))
    placeholders = ", ".join(["%s"] * len(product_ids))

    query = f"DELETE FROM product WHERE sku IN ({placeholders})"
    args = product_ids

  #execute query
  sucessfull = execute_query(query, args, action=INSERT_REMOVE)

  # if not sucessfull:
  #   flash("Error deleting customer(s)")
  
  #render main_page
  return redirect(url_for("products_index"))

@app.route("/products/update", methods=["GET"])
def products_update():
  skus = request.args.get("skus", "")
  skus = tuple(skus.split(","))

  descriptions = request.args.get("descriptions", "")
  descriptions = tuple(descriptions.split(","))

  prices = request.args.get("prices", "")
  prices = tuple(prices.split(","))

  #update products that match the sku with the new description and price
  for sku, description, price in zip(skus, descriptions, prices):
    query = "UPDATE product SET description = %s, price = %s WHERE sku = %s"
    args = (description, price, sku)
    sucessfull = execute_query(query, args, action=INSERT_REMOVE)

    # if not sucessfull:
    #   flash("Error updating product(s)")

  return redirect(url_for("products_index"))

@app.route("/ping", methods=("GET",))
def ping():
  log.debug("ping!")
  return jsonify({"message": "pong!", "status": "success"})


if __name__ == "__main__":
  app.run()
