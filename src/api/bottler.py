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
    res = [min(quantity_per_ml)]
    for i in range(len(quantity_per_ml)):
        if quantity_per_ml[i] != 100:
            res.append(mls[i] - (potion_type[i] * quantity_per_ml[i]))
        else:
            res.append(mls[i])
    return res


@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")
    with db.engine.begin() as connection:

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
            delivered_dict.append({
                "quantity": b.quantity,
                "r": b.potion_type[0],
                "g": b.potion_type[1],
                "b": b.potion_type[2],
                "d": b.potion_type[3],
            })
            for i in range(3):
                barrels_dict[i]["ml"] += b.potion_type[i] * b.quantity


        # what does "OK" do in a Json package/SQL execution
        # ANSWER: "OK" tells the receiver that no error occurred

        connection.execute(sqlalchemy.text(f"UPDATE potions SET quantity = quantity + :quantity "
                                           f"WHERE r = :r AND g = :g AND b = :b AND d = :d"), delivered_dict)

        # updates quantity of ml for all types
        connection.execute(sqlalchemy.text(f"UPDATE barrels SET ml = ml - :ml "
                                           f"WHERE barrel_type = :color"), barrels_dict)
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
        total_potions = connection.execute(sqlalchemy.text("SELECT SUM(quantity) AS total FROM potions")).scalar()

        # gets the 3 barrel types
        b = connection.execute(sqlalchemy.text("SELECT ml FROM barrels ORDER BY id ASC")).all()
        for t in b:
            barrel_types.append(t.ml)

        # gets all potion types and adds them to list of Potion objs
        # orders by quantity to prioritize potions with the lowest quantity
        t = connection.execute(sqlalchemy.text(
                "SELECT potion_sku, potion_name, quantity, R, G, B, D FROM potions ORDER BY quantity ASC")).all()
        for p in t:
            potions_types.append(Potion(p.potion_sku, p.potion_name, p.quantity, [p.r, p.g, p.b, p.d]))

    res = []
    # checks if potion capacity has been reached to add potions
    if total_potions < 85:

        # adds correct potion if there is enough ml to make it
        for p in potions_types:

            # checks how much of potion we can make depending on
            # amount of ml and changes barrels accordingly
            possible_quantity = check_ml(barrel_types, p.type_list)
            if possible_quantity[0] > 0 and possible_quantity[0] != 100:
                for i in range(len(barrel_types)):
                    barrel_types[i] = possible_quantity[i + 1]
                total_potions += possible_quantity[0]
                if total_potions > 85:
                    possible_quantity[0] -= total_potions - 85
                    if possible_quantity[0] > 0:
                        res.append({"potion_type": p.type_list,
                                    "quantity": possible_quantity[0]})
                    break
                res.append({"potion_type": p.type_list,
                            "quantity": possible_quantity[0]})
    return res
