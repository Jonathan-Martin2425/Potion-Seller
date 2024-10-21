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


# creates case for specific potion type when updating potions
def potion_update(potion_type: list[int], new_quantity: int):
    return f"WHEN r = {potion_type[0]} AND g = {potion_type[1]} AND " \
           f"b = {potion_type[2]} AND d = {potion_type[3]} THEN {new_quantity} \n"


@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")

    barrel_types = []
    potion_types = []
    with db.engine.begin() as connection:
        for t in connection.execute(sqlalchemy.text("SELECT potions, ml FROM global_inventory")):
            total_potions, ml = t

        # get number of ml for each type
        for t in connection.execute(sqlalchemy.text("SELECT ml FROM barrels ORDER BY id ASC")):
            barrel_types.append(t[0])

        # get attributes of all potion types
        for t in connection.execute(
                sqlalchemy.text("SELECT potion_sku, potion_name, quantity, R, G, B, D FROM potions ORDER BY id ASC")):
            p = (Potion(t[0], t[1], t[2], [t[3], t[4], t[5], t[6]]))
            potion_types.append(p)

    # iterates through potions delivered and all potion types
    # then adds or subtracts attributes if they match
    for b in potions_delivered:
        for p in potion_types:
            if b.potion_type == p.type_list and b.quantity > 0:
                # print("Delivered - " + str(b.potion_type) + "\nActual - " + str(p.type_list))
                total_potions += b.quantity
                ml -= POTION_TO_ML * b.quantity
                p.quantity += b.quantity
                for i in range(3):
                    barrel_types[i] -= p.type_list[i] * b.quantity

    # what does "OK" do in a Json package/SQL execution
    # ANSWER: "OK" tells the receiver that no error occurred

    # updates potions gained and potential green ml lost in creation of potions
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(f"UPDATE global_inventory SET potions = {total_potions}, ml = {ml} WHERE id= 1"))

        potion_sql = "UPDATE potions SET quantity = CASE "
        for p in potion_types:
            potion_sql += potion_update(p.type_list, p.quantity)
        potion_sql += "ELSE quantity END WHERE quantity > -1"
        # updates quantity of all potion types
        connection.execute(sqlalchemy.text(potion_sql))

        # updates quantity of ml for all types
        connection.execute(
            sqlalchemy.text(f"UPDATE barrels SET ml = CASE barrel_type WHEN 'red' THEN {barrel_types[0]} "
                            f"WHEN 'green' THEN {barrel_types[1]} "
                            f"WHEN 'blue' THEN {barrel_types[2]} "
                            f"ELSE ml END "
                            f"WHERE barrel_type IN ('red', 'green', 'blue')"))
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
        total_potions = connection.execute(sqlalchemy.text("SELECT potions FROM global_inventory")).scalar()

        # gets the 3 barrel types
        for t in connection.execute(sqlalchemy.text("SELECT ml FROM barrels ORDER BY id ASC")):
            barrel_types.append(t[0])

        # gets all potion types and adds them to list of Potion objs
        # orders by quantity to prioritize potions with the lowest quantity
        for t in connection.execute(
                sqlalchemy.text(
                    "SELECT potion_sku, potion_name, quantity, R, G, B, D FROM potions ORDER BY quantity ASC")):
            potions_types.append(Potion(t[0], t[1], t[2], [t[3], t[4], t[5], t[6]]))

    res = []
    # checks if potion capacity has been reached to add potions
    if total_potions <= 82:

        # adds correct potion if there is enough ml to make it
        for p in potions_types:

            # checks how much of potion we can make depending on
            # amount of ml and changes barrels accordingly
            possible_quantity = check_ml(barrel_types, p.type_list)
            if possible_quantity[0] > 0:
                for i in range(len(barrel_types)):
                    barrel_types[i] = possible_quantity[i + 1]
                res.append({"potion_type": p.type_list,
                            "quantity": possible_quantity[0]})
    return res
