"""
Grocery Ordering App (Prototype)
- Customer flow: choose a store -> browse products -> cart -> checkout -> confirmation
- Store flow: inventory management + view/update order status

Data is in-memory for prototype purposes (resets on restart).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-me"


# -----------------------------
# Models
# -----------------------------
@dataclass
class Product:
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
    status: str = "pending"  # pending | accepted | ready | completed


@dataclass
class Store:
    id: int
    name: str
    products: Dict[int, Product] = field(default_factory=dict)
    orders: List[Order] = field(default_factory=list)

    def next_product_id(self) -> int:
        return (max(self.products.keys()) + 1) if self.products else 1

    def next_order_id(self) -> int:
        return (max([o.id for o in self.orders]) + 1) if self.orders else 1

    def add_product(self, name: str, price: float, quantity: int) -> None:
        pid = self.next_product_id()
        self.products[pid] = Product(id=pid, name=name, price=price, quantity=quantity)

    def update_product(self, product_id: int, name: str, price: float, quantity: int) -> None:
        if product_id in self.products:
            self.products[product_id].name = name
            self.products[product_id].price = price
            self.products[product_id].quantity = quantity

    def delete_product(self, product_id: int) -> None:
        self.products.pop(product_id, None)

    def create_order(self, items: List[OrderItem], delivery_method: str) -> Order:
        # Validate & decrement inventory
        total = 0.0
        for item in items:
            product = self.products.get(item.product_id)
            if not product:
                raise ValueError("Product not found.")
            if item.quantity <= 0:
                raise ValueError("Invalid quantity.")
            if item.quantity > product.quantity:
                raise ValueError(f"Not enough stock for {product.name}.")
            total += product.price * item.quantity

        # Apply inventory decrement
        for item in items:
            self.products[item.product_id].quantity -= item.quantity

        order = Order(
            id=self.next_order_id(),
            items=items,
            total_price=round(total, 2),
            delivery_method=delivery_method,
            status="pending",
        )
        self.orders.append(order)
        return order

    def get_order(self, order_id: int) -> Optional[Order]:
        return next((o for o in self.orders if o.id == order_id), None)


# -----------------------------
# Seed data (multiple stores)
# -----------------------------
stores: Dict[int, Store] = {}

def seed() -> None:
    global stores
    s1 = Store(id=1, name="Sunnyvale Fresh Mart")
    s1.add_product("Bananas", 0.69, 100)
    s1.add_product("Milk (1 gal)", 4.49, 30)
    s1.add_product("Eggs (dozen)", 3.99, 40)

    s2 = Store(id=2, name="Neighborhood Grocers")
    s2.add_product("Apples (lb)", 1.29, 80)
    s2.add_product("Bread", 3.49, 50)
    s2.add_product("Rice (5 lb)", 7.99, 20)

    s3 = Store(id=3, name="Organic Corner")
    s3.add_product("Avocados", 1.99, 60)
    s3.add_product("Greek Yogurt", 1.49, 45)
    s3.add_product("Spinach", 2.99, 35)

    stores = {1: s1, 2: s2, 3: s3}

seed()


# -----------------------------
# Helpers (store + cart)
# -----------------------------
def get_selected_store_id() -> Optional[int]:
    sid = session.get("store_id")
    return int(sid) if sid is not None else None

def get_store_or_redirect() -> Optional[Store]:
    sid = get_selected_store_id()
    if not sid or sid not in stores:
        return None
    return stores[sid]

def cart_key(store_id: int) -> str:
    return f"cart_store_{store_id}"

def get_cart(store_id: int) -> Dict[int, int]:
    raw = session.get(cart_key(store_id), {})
    return {int(k): int(v) for k, v in raw.items()}

def save_cart(store_id: int, cart: Dict[int, int]) -> None:
    session[cart_key(store_id)] = {str(k): int(v) for k, v in cart.items()}

def cart_count(store_id: int) -> int:
    return sum(get_cart(store_id).values())


# -----------------------------
# Customer routes
# -----------------------------
@app.route("/")
def index():
    # landing: if store chosen, go browse. else go store picker.
    if get_selected_store_id() in stores:
        return redirect(url_for("customer_home"))
    return redirect(url_for("choose_store"))

@app.route("/stores")
def choose_store():
    return render_template("choose_store.html", stores=stores)

@app.route("/stores/select/<int:store_id>", methods=["POST"])
def select_store(store_id: int):
    if store_id not in stores:
        flash("Store not found.")
        return redirect(url_for("choose_store"))
    session["store_id"] = store_id
    flash(f"Selected store: {stores[store_id].name}")
    return redirect(url_for("customer_home"))

@app.route("/customer")
def customer_home():
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))
    return render_template(
        "customer_home.html",
        store=store,
        stores=stores,
        selected_store_id=store.id,
        cart_count=cart_count(store.id),
    )

@app.route("/cart")
def view_cart():
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))

    cart = get_cart(store.id)
    items = []
    total = 0.0
    for pid, qty in cart.items():
        product = store.products.get(pid)
        if product and qty > 0:
            items.append((product, qty))
            total += product.price * qty

    return render_template(
        "order.html",
        store=store,
        items=items,
        total=round(total, 2),
        cart_count=cart_count(store.id),
    )

@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id: int):
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))

    qty = int(request.form.get("quantity", "1") or 1)
    if qty <= 0:
        flash("Quantity must be at least 1.")
        return redirect(url_for("customer_home"))

    product = store.products.get(product_id)
    if not product:
        flash("Product not found.")
        return redirect(url_for("customer_home"))

    if qty > product.quantity:
        flash("Not enough stock.")
        return redirect(url_for("customer_home"))

    cart = get_cart(store.id)
    cart[product_id] = cart.get(product_id, 0) + qty

    # cap cart qty to stock
    if cart[product_id] > product.quantity:
        cart[product_id] = product.quantity

    save_cart(store.id, cart)
    flash(f"Added {qty} x {product.name} to cart.")
    return redirect(url_for("customer_home"))

@app.route("/cart/clear", methods=["POST"])
def clear_cart():
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))
    save_cart(store.id, {})
    flash("Cart cleared.")
    return redirect(url_for("view_cart"))

@app.route("/checkout", methods=["POST"])
def checkout():
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))

    delivery_method = request.form.get("delivery_method", "pickup")
    if delivery_method not in ("delivery", "pickup"):
        delivery_method = "pickup"

    cart = get_cart(store.id)
    if not cart:
        flash("Your cart is empty.")
        return redirect(url_for("view_cart"))

    items = [OrderItem(product_id=pid, quantity=qty) for pid, qty in cart.items() if qty > 0]
    try:
        order = store.create_order(items, delivery_method)
    except ValueError as e:
        flash(str(e))
        return redirect(url_for("view_cart"))

    save_cart(store.id, {})
    flash("Order placed!")
    return redirect(url_for("order_confirmation", order_id=order.id))

@app.route("/order/<int:order_id>")
def order_confirmation(order_id: int):
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))

    order = store.get_order(order_id)
    if not order:
        flash("Order not found.")
        return redirect(url_for("customer_home"))

    display_items = []
    for item in order.items:
        p = store.products.get(item.product_id)
        # product might exist with reduced qty; name still ok.
        name = p.name if p else f"Product #{item.product_id}"
        price = p.price if p else 0.0
        display_items.append((name, item.quantity, price))

    return render_template(
        "order_confirmation.html",
        store=store,
        order=order,
        items=display_items,
        cart_count=cart_count(store.id),
    )


# -----------------------------
# Store owner routes
# -----------------------------
@app.route("/store")
def store_home():
    # store owner selects which store to manage (use same selection)
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))
    return render_template("store_home.html", store=store, stores=stores, selected_store_id=store.id)

@app.route("/store/inventory")
def manage_inventory():
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))
    return render_template("manage_inventory.html", store=store)

@app.route("/store/add_product", methods=["POST"])
def add_product():
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))

    name = (request.form.get("name") or "").strip()
    try:
        price = float(request.form.get("price", "0") or 0)
        quantity = int(request.form.get("quantity", "0") or 0)
    except ValueError:
        flash("Invalid price or quantity.")
        return redirect(url_for("manage_inventory"))

    if not name:
        flash("Product name is required.")
        return redirect(url_for("manage_inventory"))

    store.add_product(name=name, price=max(price, 0.0), quantity=max(quantity, 0))
    flash("Product added.")
    return redirect(url_for("manage_inventory"))

@app.route("/store/update_product/<int:product_id>", methods=["POST"])
def update_product(product_id: int):
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))

    name = (request.form.get("name") or "").strip()
    try:
        price = float(request.form.get("price", "0") or 0)
        quantity = int(request.form.get("quantity", "0") or 0)
    except ValueError:
        flash("Invalid price or quantity.")
        return redirect(url_for("manage_inventory"))

    if not name:
        flash("Product name is required.")
        return redirect(url_for("manage_inventory"))

    store.update_product(product_id, name=name, price=max(price, 0.0), quantity=max(quantity, 0))
    flash("Product updated.")
    return redirect(url_for("manage_inventory"))

@app.route("/store/delete_product/<int:product_id>", methods=["POST"])
def delete_product(product_id: int):
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))
    store.delete_product(product_id)
    flash("Product deleted.")
    return redirect(url_for("manage_inventory"))

@app.route("/store/orders")
def view_orders():
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))
    return render_template("store_orders.html", store=store)

@app.route("/store/orders/<int:order_id>/status", methods=["POST"])
def update_order_status(order_id: int):
    store = get_store_or_redirect()
    if not store:
        return redirect(url_for("choose_store"))

    order = store.get_order(order_id)
    if not order:
        flash("Order not found.")
        return redirect(url_for("view_orders"))

    new_status = request.form.get("status", "pending")
    allowed = {"pending", "accepted", "ready", "completed"}
    if new_status not in allowed:
        flash("Invalid status.")
        return redirect(url_for("view_orders"))

    order.status = new_status
    flash(f"Order #{order.id} updated to {new_status}.")
    return redirect(url_for("view_orders"))


if __name__ == "__main__":
    app.run(debug=True)
