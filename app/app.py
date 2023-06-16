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
from datetime import datetime


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

def get_max_page(nentrys, items_per_page):
  #display n items_per_page 
  max_page = (nentrys // items_per_page)
  if nentrys % 8 != 0:
    max_page += 1
  if nentrys == 0:
    max_page = 1
  return max_page

@app.route("/", methods=["GET"])
def index():
  #render customers page by default
  return redirect(url_for("customers_index"))


########################################################

# MANAGE CUSTOMERS
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
  max_page = get_max_page(len(customers), 8)
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
  #get new customer id
  query = "SELECT MAX(cust_no) FROM customer"
  args = ()

  last_cust_no = execute_query(query, args, action=FETCH_ONE)

  cust_no = last_cust_no.max + 1 if last_cust_no.max is not None else 1
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

  # Start a transaction
  with pool.connection() as conn:
    with conn.cursor() as cur:
      try:
        # if delete_all is true, delete all customers
        if delete_all == 1:
          # Delete all payments first
          delete_payments_query = "DELETE FROM pay"
          cur.execute(delete_payments_query)

          # Delete associated contains first
          delete_contains_query = "DELETE FROM contains"
          cur.execute(delete_contains_query)

          # Delete associated orders first
          delete_orders_query = "DELETE FROM orders"
          cur.execute(delete_orders_query)

          # Then delete all customers
          query = "DELETE FROM customer"
          cur.execute(query)
        else:
          # parse ids
          customer_ids = tuple(map(int, customer_ids.split(",")))
          placeholders = ", ".join(["%s"] * len(customer_ids))

          #delete associated payments for the selected customers
          delete_payments_query = f"DELETE FROM pay WHERE cust_no IN ({placeholders})"
          cur.execute(delete_payments_query, args)

          # Delete associated contains for the selected customers
          delete_contains_query = f"DELETE FROM contains WHERE cust_no IN ({placeholders})"
          cur.execute(delete_contains_query, args)

          # Delete associated orders for the selected customers
          delete_orders_query = f"DELETE FROM orders WHERE cust_no IN ({placeholders})"
          cur.execute(delete_orders_query, args)

          # Then delete the selected customers
          query = f"DELETE FROM customer WHERE cust_no IN ({placeholders})"
          args = customer_ids
          cur.execute(query, args)

        # Commit the transaction
        conn.commit()
      except:
        log.exception("Error deleting customer")
        # Rollback the transaction
        conn.rollback()

  # Render main_page
  return redirect(url_for("customers_index"))

########################################################

# MANAGE PRODUCTS
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
  max_page = get_max_page(len(products), 8)
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
  product_ids = request.args.get("skus", "")

  # if product_ids == "":
  #   flash("Please select a product to remove")
  #   return redirect(url_for("products_index"))

  #if delete_all is true, delete all customers
  # Start a transaction
  with pool.connection() as conn:
    with conn.cursor() as cur:
      try:
        # if delete_all is true, delete all customers
        if delete_all == 1:
          #delete associated supliers first
          delete_supplies_query = "DELETE FROM supplier"
          cur.execute(delete_supplies_query)
          
          query = "DELETE FROM product"
          args = ()
          cur.execute(query)
        else:
          #parse ids
          product_ids = tuple(product_ids.split(","))
          placeholders = ", ".join(["%s"] * len(product_ids))

          query = f"DELETE FROM product WHERE sku IN ({placeholders})"
          args = product_ids

        # Commit the transaction
        conn.commit()
      except:
        log.exception("Error deleting customer")
        # Rollback the transaction
        conn.rollback()
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

########################################################

# MANAGE SUPPLIERS
@app.route("/suppliers", methods=["GET"])
def suppliers_index():
  #get filter arg from request
  name_q = request.args.get("q", "")
  page = int(request.args.get("page", 1))

  if name_q == "":
    #run query without filter
    query = "SELECT * FROM supplier"
    args = ()
  else:
    query = "SELECT * FROM supplier WHERE name ILIKE %s OR tin ILIKE %s"
    args = (name_q, name_q)

  suppliers = execute_query(query, args, action=FETCH_ALL)

  #display 8 suppliers per page
  max_page = get_max_page(len(suppliers), 8)
  suppliers = suppliers[(page-1)*8:page*8]

  return render_template(
    "/suppliers/index.html",
    navbar_text="Suppliers",
    current_q=name_q,
    current_page=page,
    max_page=max_page,
    search_label="Search by tin or name..",
    suppliers=suppliers
  ) 

# ADD SUPPLIER
@app.route("/suppliers/add", methods=["GET"])
def suppliers_add():
  random_no = randint(0, 999999)
  tin = request.args.get("tin", random_no)
  name = request.args.get("name", f"n-{random_no}")
  address = request.args.get("address", "debug")
  sku = request.args.get("sku", "d-251918")
  date = request.args.get("date", "2020-01-01")

  # if tin is None or name is None or address is None or sku is None or date is None:
  #   flash("Please fill out all fields")

  #create query
  query = "INSERT INTO supplier (tin, name, address, sku, date) VALUES (%s, %s, %s, %s, %s)"
  args = (tin, name, address, sku, date)

  #insert customer into db
  sucessfull = execute_query(query, args, action=INSERT_REMOVE)
  # if not sucessfull:
  #   flash("Error inserting customer")
  
  #render main_page
  return redirect(url_for("suppliers_index"))

# REMOVE SUPPLIER
@app.route("/suppliers/delete", methods=["GET"])
def suppliers_remove():
  delete_all = int(request.args.get("all", 0))
  tins = request.args.get("tins", "")

  # if tins == "":
  #   flash("Please select a supplier to remove")
  #   return redirect(url_for("suppliers_index"))

  #if delete_all is true, delete all customers
  if delete_all == 1:
    query = "DELETE FROM supplier"
    args = ()
  else:
    #parse ids
    tins = tuple(tins.split(","))
    placeholders = ", ".join(["%s"] * len(tins))

    query = f"DELETE FROM supplier WHERE tin IN ({placeholders})"
    args = tins

  #execute query
  sucessfull = execute_query(query, args, action=INSERT_REMOVE)

  # if not sucessfull:
  #   flash("Error deleting supplier(s)")
  
  #render main_page
  return redirect(url_for("suppliers_index"))

########################################################

#MANAGE ORDER
@app.route("/orders", methods=["GET"])
def orders_index():
  #get filter arg from request
  page = int(request.args.get("page", 1))

  #run query without filter
  query = "SELECT o.*, CASE WHEN p.order_no IS NOT NULL THEN 'Paid' ELSE 'Waiting for payment' END AS paid FROM orders o LEFT JOIN pay p ON o.order_no = p.order_no;"
  args = ()

  orders = execute_query(query, args, action=FETCH_ALL)

  #display 8 products per page
  max_page = get_max_page(len(orders), 8)
  orders = orders[(page-1)*8:page*8]

  return render_template(
    "/orders/index.html",
    navbar_text="Orders", 
    search_available=False,
    current_page=page,
    max_page=max_page,
    search_label="Search by order_no or cust_no",
    orders=orders
  )


# ORDER REROUTE
@app.route("/order", methods=["GET"])
def order_index():
  customers = execute_query("SELECT * FROM customer", (), action=FETCH_ALL)

  order_no = request.args.get("order_no", "")
  if order_no:
    #get cust_no
    cust_no = request.args.get("cust_no", "")

    #get order contains
    query = "SELECT p.sku, p.name, p.description, p.price, p.ean, c.qty FROM contains c JOIN product p ON c.sku = p.sku WHERE c.order_no = %s;"
    args = (order_no,)
    order = execute_query(query, args, action=FETCH_ALL)

    return render_template("/order/index.html", 
      navbar_text="Order - Payment",
      search_available=False,
      order_exists=True,
      order=order,
      order_no=order_no,
      cust_no=cust_no
    )

  skus = request.args.get("skus", "")
  skus = tuple(skus.split(","))

  names = request.args.get("names", "")
  names = tuple(names.split(","))

  descriptions = request.args.get("descriptions", "")
  descriptions = tuple(descriptions.split(","))

  prices = request.args.get("prices", "")
  prices = tuple(prices.split(","))

  eans = request.args.get("eans", "")
  eans = tuple(eans.split(","))

  order = list(zip(skus, names, descriptions, prices, eans))

  return render_template("/order/index.html",
    navbar_text="Order Placing", 
    search_available=False, 
    order_exist=False,
    order=order,
    customers=customers
  )

@app.route("/order/place", methods=["GET"])
def order_place():
  #current date in format YYYY-MM-DD
  date = datetime.now().strftime("%Y-%m-%d")
  
  # create order row
  latest_order = execute_query("SELECT MAX(order_no) FROM orders", (), action=FETCH_ONE)
  order_no = latest_order[0] + 1 if latest_order[0] else 1
  cust_no = request.args.get("cust_no", 1)
  
  skus = request.args.get("skus", "")
  skus = tuple(skus.split(","))

  quantities = request.args.get("quantities", "")
  quantities = tuple(quantities.split(","))

  #insert into orders table
  query = "INSERT INTO orders (order_no, cust_no, date) VALUES (%s, %s, %s)"
  args = (order_no, cust_no, date)
  sucessfull = execute_query(query, args, action=INSERT_REMOVE)

  #insert into contains
  for sku, quantity in zip(skus, quantities):
    query = "INSERT INTO contains (order_no, sku, qty) VALUES (%s, %s, %s)"
    args = (order_no, sku, quantity)
    sucessfull = execute_query(query, args, action=INSERT_REMOVE)

  #render main_page
  return redirect(url_for("order_index", order_no=order_no, cust_no=cust_no))

@app.route("/order/pay", methods=["GET"])
def order_pay():
  order_no = request.args.get("order_no", "")
  cust_no = request.args.get("cust_no", "")
  
  #insert in pay
  query = "INSERT INTO pay (order_no, cust_no) VALUES (%s, %s)"
  args = (order_no, cust_no)
  sucessfull = execute_query(query, args, action=INSERT_REMOVE)

  #render main_page
  return redirect(url_for("orders_index"))


if __name__ == "__main__":
  app.run()
