from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET potions= 0, gold= 0 WHERE id= 1"))

        # updates quantity of all potion types
        connection.execute(sqlalchemy.text("UPDATE potions SET quantity= 0"))

        # updates quantity of ml for all types
        connection.execute(sqlalchemy.text("UPDATE barrels SET ml = 0"))

        #resets all cart orders, leaving only 1 default as a place holder
        connection.execute(sqlalchemy.text("DELETE FROM cart_orders WHERE NOT cart_id = 1"))


    return "OK"

