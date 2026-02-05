"""
Main application for the grocery ordering system.

This Flask application provides two interfaces:

1. **Customer interface** at `/` where shoppers can browse products, add items
   to a cart and place orders for delivery or pickup.
2. **Store owner interface** at `/store` where inventory can be managed and
   orders reviewed.

The app uses in‑memory dictionaries to simulate a simple data store.  It is
intended as a prototype; for a production system you would integrate a
database and authentication.
"""

from __future__ import annotations

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash)
from dataclasses import dataclass, field
from typing import Dict, List

app = Flask(__name__)
app.secret_key = "super_secret_key"  # Replace with a secure random key in production


@dataclass
class Product:
    """Represents a product in the store."""
    id: int
    name: str
    price: float
    quantity: int


@dataclass
class OrderItem:
    product_id: int
    quantity: int


@dataclass
class Order:
    id: int
    items: List[OrderItem]
    total_price: float
    delivery_method: str  # "delivery" or "pickup"


@dataclass
class Store:
    id: int
    name: str
    products: Dict[int, Product] = field(default_factory=dict)
    orders: List[Order] = field(default_factory=list)

    def add_product(self, name: str, price: float, quantity: int) -> None:
        new_id = max(self.products.keys(), default=0) + 1
        self.products[new_id] = Product(new_id, name, price, quantity)

    def update_product(self, product_id: int, name: str, price: float, quantity: int) -> None:
        if product_id in self.products:
            self.products[product_id].name = name
            self.products[product_id].price = price
            self.products[product_id].quantity = quantity

    def delete_product(self, product_id: int) -> None:
        if product_id in self.products:
            del self.products[product_id]

    def create_order(self, items: List[OrderItem], delivery_method: str) -> Order:
        total = 0.0
        # Update quantities and compute total
        for item in items:
            product = self.products.get(item.product_id)
            if not product or item.quantity > product.quantity:
                raise ValueError("Invalid item quantity")
            total += product.price * item.quantity
            product.quantity -= item.quantity
        order_id = (self.orders[-1].id + 1) if self.orders else 1
        order = Order(id=order_id, items=items, total_price=total, delivery_method=delivery_method)
        self.orders.append(order)
        return order


# Initialize a single store with sample products
store = Store(id=1, name="Neighborhood Market")
store.add_product("Apple", 0.99, 50)
store.add_product("Banana", 0.59, 40)
store.add_product("Bread", 2.49, 20)


def get_cart() -> Dict[int, int]:
    """Retrieve the current cart from the session."""
    return session.get("cart", {})


def save_cart(cart: Dict[int, int]) -> None:
    """Save the current cart to the session."""
    session["cart"] = cart


@app.route('/')
def customer_home():
    """Display list of products and cart summary to the customer."""
    cart = get_cart()
    cart_count = sum(cart.values())
    return render_template(
        'customer_home.html',
        store=store,
        cart_count=cart_count,
    )


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id: int):
    """Add an item to the cart."""
    quantity = int(request.form.get('quantity', 1))
    cart = get_cart()
    current = cart.get(product_id, 0)
    # ensure not exceeding stock
    product = store.products.get(product_id)
    if product and current + quantity <= product.quantity:
        cart[product_id] = current + quantity
        save_cart(cart)
        flash(f"Added {quantity} × {product.name} to cart.")
    else:
        flash("Unable to add item – not enough stock.")
    return redirect(url_for('customer_home'))


@app.route('/cart')
def view_cart():
    """Display the current shopping cart."""
    cart = get_cart()
    items = []
    total = 0.0
    for pid, qty in cart.items():
        product = store.products.get(pid)
        if product:
            items.append((product, qty))
            total += product.price * qty
    return render_template('order.html', items=items, total=total)


@app.route('/place_order', methods=['POST'])
def place_order():
    """Place the customer's order and clear the cart."""
    cart = get_cart()
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for('customer_home'))
    delivery_method = request.form.get('delivery_method', 'pickup')
    items = [OrderItem(product_id=pid, quantity=qty) for pid, qty in cart.items()]
    try:
        order = store.create_order(items, delivery_method)
        save_cart({})  # clear cart
        return redirect(url_for('order_confirmation', order_id=order.id))
    except ValueError as e:
        flash(str(e))
        return redirect(url_for('view_cart'))


@app.route('/order/<int:order_id>')
def order_confirmation(order_id: int):
    """Show confirmation page for a placed order."""
    order = next((o for o in store.orders if o.id == order_id), None)
    if not order:
        flash("Order not found.")
        return redirect(url_for('customer_home'))
    # Build list of product details
    items_details = []
    for item in order.items:
        product = store.products.get(item.product_id)
        # Note: product quantity updated after order
        name = product.name if product else 'Unknown'
        items_details.append((name, item.quantity, product.price if product else 0.0))
    return render_template(
        'order_confirmation.html',
        order=order,
        items=items_details,
    )


@app.route('/store')
def store_home():
    """Display the store owner dashboard."""
    return render_template('store_home.html', store=store)


@app.route('/store/inventory')
def manage_inventory():
    """Display inventory management page."""
    return render_template('manage_inventory.html', store=store)


@app.route('/store/add_product', methods=['POST'])
def add_product():
    """Add a new product to the store."""
    name = request.form.get('name')
    price = float(request.form.get('price', '0'))
    quantity = int(request.form.get('quantity', '0'))
    if name:
        store.add_product(name, price, quantity)
        flash(f"Added product {name}.")
    return redirect(url_for('manage_inventory'))


@app.route('/store/update_product/<int:product_id>', methods=['POST'])
def update_product(product_id: int):
    """Update an existing product."""
    name = request.form.get('name')
    price = float(request.form.get('price', '0'))
    quantity = int(request.form.get('quantity', '0'))
    store.update_product(product_id, name, price, quantity)
    flash(f"Updated product {name}.")
    return redirect(url_for('manage_inventory'))


@app.route('/store/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id: int):
    """Remove a product from the store."""
    store.delete_product(product_id)
    flash("Product removed.")
    return redirect(url_for('manage_inventory'))


@app.route('/store/orders')
def view_orders():
    """Display a list of customer orders for the store owner."""
    return render_template('store_orders.html', store=store)


if __name__ == '__main__':
    app.run(debug=True)