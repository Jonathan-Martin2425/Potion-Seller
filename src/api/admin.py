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
        # resets both ledgers, leaving only 1st with default 100 gold
        connection.execute(sqlalchemy.text("DELETE FROM ledger WHERE NOT id = 1"))
        connection.execute(sqlalchemy.text("DELETE FROM barrel_ledger"))

        # resets cart order and item tables
        connection.execute(sqlalchemy.text("DELETE FROM cart_items WHERE NOT id = 1"))
        connection.execute(sqlalchemy.text("DELETE FROM cart_orders WHERE NOT id = 1"))

        # sets ml and potion capacity back to 0
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET "
                                           f"potion_capacity = 0,"
                                           f"barrel_capacity = 0"))

    return "OK"
