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
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    barrels_types = []
    potion_types = []
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("SELECT potions FROM global_inventory")).scalar()
        ml = connection.execute(sqlalchemy.text("SELECT ml FROM global_inventory")).scalar()

        # get number of ml for each type
        barrels_types.append(
            connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'red'")).scalar())
        barrels_types.append(
            connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'green'")).scalar())
        barrels_types.append(
            connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'blue'")).scalar())

        # get quantity of all potion types
        potion_types.append(
            connection.execute(sqlalchemy.text("SELECT quantity FROM potions WHERE potion_type= 'red'")).scalar())
        potion_types.append(
            connection.execute(sqlalchemy.text("SELECT quantity FROM potions WHERE potion_type= 'green'")).scalar())
        potion_types.append(
            connection.execute(sqlalchemy.text("SELECT quantity FROM potions WHERE potion_type= 'blue'")).scalar())

    # iterates through potions delivered and adds or subtracts attributes
    # according to the potions type
    for b in potions_delivered:
        if b.potion_type[0] == 100 and b.quantity > 0:
            potions += b.quantity
            ml -= POTION_TO_ML
            barrels_types[0] -= POTION_TO_ML
            potion_types[0] += b.quantity
        if b.potion_type[1] == 100 and b.quantity > 0:
            potions += b.quantity
            ml -= POTION_TO_ML
            barrels_types[1] -= POTION_TO_ML
            potion_types[1] += b.quantity
        if b.potion_type[2] == 100 and b.quantity > 0:
            potions += b.quantity
            ml -= POTION_TO_ML
            potion_types[2] += b.quantity
            barrels_types[2] -= POTION_TO_ML

    # what does "OK" do in a Json package/SQL excecution
    # ANSWER: "OK" tells the reciever that no error occurred

    # updates potions gained and potential green ml lost in creation of potions
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET potions = {potions} WHERE id= 1"))
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET potions = {ml} WHERE id= 1"))

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
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("SELECT potions FROM global_inventory")).scalar()
        redMl = connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'red'")).scalar()
        greenMl = connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'green'")).scalar()
        blueMl = connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'blue'")).scalar()

    res = []
    # checks if potion capacity has been reached to add potions
    if potions <= 82:

        # adds correct potion if there is enough ml of it
        if redMl >= 100:
            res.append({"potion_type": [100, 0, 0, 0],
                        "quantity": 1})
        if greenMl >= 100 != "":
            res.append({"potion_type": [0, 100, 0, 0],
                        "quantity": 1})
        if blueMl >= 100 != "":
            res.append({"potion_type": [0, 0, 100, 0],
                        "quantity": 1})
    return res
