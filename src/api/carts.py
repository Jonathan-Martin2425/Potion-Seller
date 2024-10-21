from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

with db.engine.begin() as connection:
    result = connection.execute(sqlalchemy.text("SELECT cart_id FROM cart_orders ORDER BY cart_id DESC"))
    for res in result:
        cur_cart_id = res[0] + 1
        break


# takes parameters for correct API response
# returns correct json format
def cart_json(num_potions: int = None, payment: int = None):
    if num_potions is not None and payment is not None:
        return {"total_potions_bought": num_potions,
                "total_gold_paid": payment}
    else:
        return {"total_potions_bought": 0,
                "total_gold_paid": 0}


class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"


class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"


@router.get("/search/", tags=["search"])
def search_orders(
        customer_name: str = "",
        potion_sku: str = "",
        search_page: str = "",
        sort_col: search_sort_options = search_sort_options.timestamp,
        sort_order: search_sort_order = search_sort_order.desc,

):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "GREEN_POTION",
                "customer_name": "Scaramouche",
                "line_item_total": 20,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int


# Represents a potion's attributes per row on the potions table
class Potion:
    sku: str
    quantity: int
    type_list: list[int]
    name: str

    def __init__(self, sku: str, name: str, quantity: int, type_list: list[int]):
        self.sku = sku
        self.name = name
        self.quantity = quantity
        self.type_list = type_list

    def __repr__(self):
        return "Sku: " + self.sku + " Name: " + self.name + " quantity: " + str(self.quantity) + " type: " + str(
            self.type_list)


# creates case for specific potion type when updating potions
def potion_update(potion_type: list[int], new_quantity: int):
    return f"WHEN r = {potion_type[0]} AND g = {potion_type[1]} AND " \
           f"b = {potion_type[2]} AND d = {potion_type[3]} THEN {new_quantity} \n"


@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(customers)

    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    global cur_cart_id
    temp = cur_cart_id
    cur_cart_id = cur_cart_id + 1
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"INSERT INTO cart_orders (cart_id, name, class, level) "
                                           f"VALUES ({temp}, '{new_cart.customer_name}', "
                                           f"'{new_cart.character_class}', {new_cart.level})"))
    return {"cart_id": temp}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ takes requested potion and ammount(CartItem)
        and sets their order in supabase using their ID"""

    # creates cart item of given cart_id into cart_items table
    # where the cart_id and item_sku work as the 2 foreign keys for
    # cart_orders and potions tables respectively
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"INSERT INTO cart_items (cart_id, item_sku, quantity) "
                                           f"VALUES ({cart_id}, '{item_sku}', {cart_item.quantity})"))
    print("Set Quantity: " + str(cart_item.quantity))
    return "OK"


class CartCheckout(BaseModel):
    payment: str


@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    # checks if customer wanted to  buy something
    with db.engine.begin() as connection:
        # gets attributes from global inventory table
        for i in connection.execute(sqlalchemy.text("SELECT potions, gold FROM global_inventory")):
            total_potions, gold = i

        # gets all potion types
        potion_types = []
        for t in connection.execute(
                sqlalchemy.text("SELECT potion_sku, potion_name, quantity, R, G, B, D FROM potions ORDER BY id ASC")):
            p = (Potion(t[0], t[1], t[2], [t[3], t[4], t[5], t[6]]))
            potion_types.append(p)

        # gets order from order id
        order = []
        for item in connection.execute(
                sqlalchemy.text(f"SELECT item_sku, quantity FROM cart_items WHERE cart_id= {cart_id}")):
            order.append(item)

        if order[0][1] > 0:
            print("Payment type: " + cart_checkout.payment)

            # updates global_inventory attributes
            gold += 100 * order[0][1]
            total_potions -= order[0][1]

            # updates potion quantity ordered depending on the order's item_sku
            for i in range(len(potion_types)):
                if potion_types[i].sku == order[0][0]:
                    potion_types[i].quantity -= order[0][1]

        # updates global inventory attributes
        connection.execute(
            sqlalchemy.text(f"UPDATE global_inventory SET gold = {gold}, potions = {total_potions} WHERE id= 1"))

        # updates quantity of all potion types
        potion_sql = "UPDATE potions SET quantity = CASE "
        for p in potion_types:
            potion_sql += potion_update(p.type_list, p.quantity)
        potion_sql += "ELSE quantity END WHERE quantity > -1"
        connection.execute(sqlalchemy.text(potion_sql))
    # gives receipt back to customer as response
    if order[0][1] > 0:
        return cart_json(order[0][1], 100 * order[0][1])
    else:
        return cart_json()
