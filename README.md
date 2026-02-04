# Grocery Ordering App

This repository contains a simple prototype for a grocery ordering application that allows customers to order groceries from local small stores for delivery or pickup.  The app is built with **Flask**, a lightweight Python web framework, and uses server‑rendered HTML templates to provide two separate interfaces—one for customers and another for store owners/managers.

## Features

### Customer Interface

- Browse the list of available stores.
- View available products at a selected store.
- Add items to a cart and place an order for delivery or pickup.
- Receive a confirmation page summarizing the order.

### Store Owner/Manager Interface

- Log in as a store owner to manage inventory.
- Add new products with name, price and quantity.
- Edit or remove existing products.
- View a list of incoming orders.

## Getting Started

### Prerequisites

This project requires **Python 3.8** or later.  To install the dependencies, create a virtual environment and install from `requirements.txt`:

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the Application

Launch the development server by running the `app.py` script:

```
python app.py
```

By default the application listens on port 5000.  Access the customer interface at [http://localhost:5000/](http://localhost:5000/) and the store owner interface at [http://localhost:5000/store](http://localhost:5000/store).

## Project Structure

```
grocery-ordering-app/
├── app.py              # main application
├── requirements.txt    # Python dependencies
├── templates/          # Jinja2 templates for HTML pages
│   ├── base.html
│   ├── customer_home.html
│   ├── store_home.html
│   ├── order.html
│   └── manage_inventory.html
└── static/
        └── css/style.css  # basic styling
```

This code is intended as a starting point and can be expanded with authentication, database integration and improved user experience.
