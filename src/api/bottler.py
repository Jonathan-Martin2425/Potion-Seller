from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

POTION_TO_ML = 100  # ammount of ml required to make a potion


class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int


@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")

    barrels_types = []
    potion_types = []
    with db.engine.begin() as connection:
        for t in connection.execute(sqlalchemy.text("SELECT potions, ml FROM global_inventory")):
            potions, ml = t

        # get number of ml for each type
        for t in connection.execute(sqlalchemy.text("SELECT ml FROM barrels ORDER BY id ASC")):
            barrels_types.append(t[0])

        # get quantity of all potion types
        for t in connection.execute(sqlalchemy.text("SELECT quantity FROM potions ORDER BY id ASC")):
            potion_types.append(t[0])

    # iterates through potions delivered and adds or subtracts attributes
    # according to the potions type
    for b in potions_delivered:
        for i in range(3):
            if b.potion_type[i] == 100 and b.quantity > 0:
                potions += b.quantity
                ml -= POTION_TO_ML
                barrels_types[i] -= POTION_TO_ML
                potion_types[i] += b.quantity

    # what does "OK" do in a Json package/SQL excecution
    # ANSWER: "OK" tells the reciever that no error occurred

    # updates potions gained and potential green ml lost in creation of potions
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET potions = {potions}, ml = {ml} WHERE id= 1"))

        # updates quantity of all potion types
        connection.execute(sqlalchemy.text(
            f"UPDATE potions SET quantity = {potion_types[0]} WHERE potion_type= 'red'"))
        connection.execute(sqlalchemy.text(
            f"UPDATE potions SET quantity = {potion_types[1]} WHERE potion_type= 'green'"))
        connection.execute(sqlalchemy.text(
            f"UPDATE potions SET quantity = {potion_types[2]} WHERE potion_type= 'blue'"))

        # updates quantity of ml for all types
        connection.execute(sqlalchemy.text(
            f"UPDATE barrels SET ml = {barrels_types[0]} WHERE barrel_type= 'red'"))
        connection.execute(sqlalchemy.text(
            f"UPDATE barrels SET ml = {barrels_types[1]} WHERE barrel_type= 'green'"))
        connection.execute(sqlalchemy.text(
            f"UPDATE barrels SET ml = {barrels_types[2]} WHERE barrel_type= 'blue'"))

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
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("SELECT potions FROM global_inventory")).scalar()
        for t in connection.execute(sqlalchemy.text("SELECT ml FROM barrels ORDER BY id ASC")):
            barrel_types.append(t[0])

    res = []
    # checks if potion capacity has been reached to add potions
    if potions <= 82:

        # adds correct potion if there is enough ml of it
        if barrel_types[0] >= 100:
            res.append({"potion_type": [100, 0, 0, 0],
                        "quantity": 1})
        if barrel_types[1] >= 100 != "":
            res.append({"potion_type": [0, 100, 0, 0],
                        "quantity": 1})
        if barrel_types[2] >= 100 != "":
            res.append({"potion_type": [0, 0, 100, 0],
                        "quantity": 1})
    return res
