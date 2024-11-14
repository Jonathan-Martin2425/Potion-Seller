from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
import math

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

POTION_TO_ML = 100  # ammount of ml required to make a potion


class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int


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


# takes in a potion type and total ml for barrels
# returns amount of potion type that can be made at index 0
# and amount of each barrel on indexes 1-3
def check_ml(mls: list[int], potion_type: list[int]) -> list[int]:
    quantity_per_ml = []
    for i in range(len(mls)):
        if potion_type[i] != 0:
            possible_quantity = math.floor(mls[i] / potion_type[i])
            if possible_quantity > 5:
                quantity = 5
            else:
                quantity = possible_quantity

            # if quantity is 0, then no potions can be made
            # since this color is required to make the potion
            # returns quantity 0 and no changes to mls, otherwise appends possible quantity
            if quantity <= 0:
                return [0, mls[0], mls[1], mls[2]]
            quantity_per_ml.append(quantity)
        else:
            quantity_per_ml.append(100)

    quantity_res = min(quantity_per_ml)
    res = [quantity_res,
           mls[0] - (potion_type[0] * quantity_res),
           mls[1] - (potion_type[1] * quantity_res),
           mls[2] - (potion_type[2] * quantity_res),]
    return res


@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")
    with db.engine.begin() as connection:

        potion_types = []
        t = connection.execute(sqlalchemy.text("SELECT potion_sku, r, g, b, d FROM potions"))
        for p in t:
            potion_types.append(Potion(p.potion_sku, "", 0, [p.r, p.g, p.b, p.d]))

        # iterates through potions delivered and all potion types
        # then adds or subtracts attributes if they match
        delivered_dict = []
        barrels_dict = [{
            "ml": 0,
            "color": 'red'
            },
            {
                "ml": 0,
                "color": 'green'
            },
            {
                "ml": 0,
                "color": 'blue'
            }]
        for b in potions_delivered:

            # iterates through each potion type to find the correct sku given the type list
            potion_sku = ""
            for p in potion_types:
                if p.type_list == b.potion_type:
                    potion_sku = p.sku

            # adds values to be inserted into ledgers
            delivered_dict.append({
                "quantity": b.quantity,
                "sku": potion_sku
            })
            for i in range(3):
                barrels_dict[i]["ml"] -= b.potion_type[i] * b.quantity

        connection.execute(sqlalchemy.text(f"INSERT INTO ledger (customer_name, sku, quantity, order_id) VALUES "
                                           f"('Goblin the Great', :sku, :quantity, {order_id})"), delivered_dict)

        # updates quantity of ml for all types
        connection.execute(sqlalchemy.text(f"INSERT INTO barrel_ledger (type, ml, order_id) VALUES "
                                           f"(:color, :ml, {order_id})"), barrels_dict)
    return []


@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # gets potion amounts and ml amounts
    barrel_types = []
    potions_types = []
    with db.engine.begin() as connection:

        # gets potion_capacity
        p_capacity = connection.execute(sqlalchemy.text("SELECT potion_capacity FROM global_inventory "
                                                        "WHERE id = 1")).scalar()
        p_capacity = (p_capacity + 1) * 50

        # gets the 3 barrel types
        t = connection.execute(sqlalchemy.text("SELECT barrel_type, SUM(barrel_ledger.ml) AS total FROM barrels "
                                               "LEFT JOIN barrel_ledger ON type = barrel_type  "
                                               "GROUP BY barrel_type "
                                               "ORDER BY barrel_type DESC")).all()
        for b in t:
            if b.total is not None:
                barrel_types.append(int(b.total))
            else:
                barrel_types.append(0)
        print("mls: " + str(barrel_types))


        # gets all potion types and adds them to list of Potion objs
        # orders by quantity to prioritize potions with the lowest quantity
        t = connection.execute(sqlalchemy.text(
                "SELECT potion_sku, potion_name, SUM(ledger.quantity) AS total, r, g, b, d FROM potions "
                "LEFT JOIN ledger ON sku = potion_sku "
                "GROUP BY potion_sku, potion_name, r, g, b, d "
                "ORDER BY total ASC")).all()

        total_potions = 0
        for p in t:
            if p.total is not None:
                total_potions += p.total
                potions_types.append(Potion(p.potion_sku, p.potion_name, p.total, [p.r, p.g, p.b, p.d]))
            else:
                potions_types.append(Potion(p.potion_sku, p.potion_name, 0, [p.r, p.g, p.b, p.d]))

    res = []
    # checks if potion capacity has been reached to add potions
    if total_potions < ((p_capacity + 1) * 50):
        # adds correct potion if there is enough ml to make it
        for p in potions_types:

            # prevent making anymore a potion type if there is
            # already >40% of our capacity of it in inventory
            if p.quantity > math.floor(p_capacity * 0.3):
                continue

            # checks how much of potion we can make depending on
            # amount of ml and changes barrels accordingly
            possible_quantity = check_ml(barrel_types, p.type_list)
            if possible_quantity[0] > 0 and possible_quantity[0] != 100:
                for i in range(len(barrel_types)):
                    barrel_types[i] = possible_quantity[i + 1]
                total_potions += possible_quantity[0]
                if total_potions > ((p_capacity + 1) * 50):
                    possible_quantity[0] -= total_potions - 85
                    if possible_quantity[0] > 0:
                        res.append({"potion_type": p.type_list,
                                    "quantity": possible_quantity[0]})
                    break
                res.append({"potion_type": p.type_list,
                            "quantity": possible_quantity[0]})
    return res
