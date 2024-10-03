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

POTION_TO_ML = 100 #ammount of ml required to make a potion

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar()
        greenML = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar()

    for b in potions_delivered:
        if b.potion_type[1] == 100 and b.quantity > 0:
            potions += b.quantity
            greenML -= POTION_TO_ML


    #what does "OK" do in a Json package/SQL excecution
    #ANSWER: "OK" tells the reciever that no error occurred


    #updates potions gained and potential green ml lost in creation of potions
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_potions = {potions} WHERE id= 1"))
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_ml = {greenML} WHERE id= 1"))

    return []

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.


    #tries to make 5 green potions
    with db.engine.begin() as connection:
        greenMl = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar()
    if greenMl > 0:
        return [
                {
                    "potion_type": [0, 100, 0, 0],
                    "quantity": 1,
                }
            ]
    else:
        return []