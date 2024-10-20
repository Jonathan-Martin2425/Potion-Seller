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
        connection.execute(sqlalchemy.text(f"INSERT INTO cart_orders (cart_id) VALUES ({temp})"))
    return {"cart_id": temp}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ takes requested potion and ammount(CartItem)
        and sets their order in supabase using their ID"""
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"UPDATE cart_orders "
                                           f"SET item_sku= '{item_sku}', quantity= {cart_item.quantity} "
                                           f"WHERE cart_id= {cart_id}"))
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

        # gets data from cart order and potions table
        res1 = connection.execute(sqlalchemy.text("SELECT quantity FROM potions ORDER BY id ASC"))
        potion_types = []
        for item in res1:
            potion_types.append(item[0])
        res2 = connection.execute(sqlalchemy.text(f"SELECT item_sku, quantity FROM cart_orders WHERE cart_id= {cart_id}"))
        order = []
        for item in res2:
            order.append(item)

        if order[0][1] > 0:
            print("Payment type: " + cart_checkout.payment)

            # updates global_inventory attributes
            gold += 100 * order[0][1]
            total_potions -= order[0][1]

            # updates potion table variables depending on the order's item_sku and quantity
            if "RED_POTION" in order[0][0]:
                potion_types[0] -= order[0][1]
            elif "GREEN_POTION" in order[0][0]:
                potion_types[1] -= order[0][1]
            elif "BLUE_POTION" in order[0][0]:
                potion_types[2] -= order[0][1]

        # updates changes to supabase
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {gold}, potions = {total_potions} WHERE id= 1"))
        connection.execute(
            sqlalchemy.text(f"UPDATE potions SET quantity = CASE potion_type WHEN 'red' THEN {potion_types[0]} "
                            f"WHEN 'green' THEN {potion_types[1]} "
                            f"WHEN 'blue' THEN {potion_types[2]} "  
                            f"ELSE quantity END "
                            f"WHERE potion_type IN ('red', 'green', 'blue')"))
    # gives receipt back to customer as response
    if order[0][1] > 0:
        return cart_json(order[0][1], new_cost * order[0][1])
    else:
        return cart_json()
