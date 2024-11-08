from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)


@router.get("/audit")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        ml = connection.execute(sqlalchemy.text("SELECT SUM(ml) AS total_ml FROM barrels")).scalar()
        potions = connection.execute(sqlalchemy.text("SELECT SUM(quantity) AS total_potions FROM potions")).scalar()
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
        return {"number_of_potions": potions, "ml_in_barrels": ml, "gold": gold}


# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    with db.engine.begin() as connection:

        # gets values to determine plan
        values = connection.execute(sqlalchemy.text("SELECT gold, potion_capacity, barrel_capacity "
                                                    "FROM global_inventory WHERE id = 1")).one()
        gold = values.gold
        p_capacity = values.potion_capacity
        b_capacity = values.barrel_capacity

        # manually adds capacity and sets them and price
        # if there is enough gold
        if gold > 5000 and p_capacity < 2:
            price = (2 - p_capacity) * 2000
            new_pCapacity = 2
            new_bCapacity = 2
        elif gold > 2500 and p_capacity < 1:
            price = (1 - p_capacity) * 2000
            new_pCapacity = 1
            new_bCapacity = 1
        else:
            price = 0
            new_pCapacity = p_capacity
            new_bCapacity = b_capacity

        # updates global_inventory regardless if a change occurred
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = gold - {price}, "
                                           f"potion_capacity = {new_pCapacity},"
                                           f"barrel_capacity = {new_bCapacity}"))
        return {
            "potion_capacity": new_pCapacity,
            "ml_capacity": new_bCapacity
        }


class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int


# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase: CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return "OK"
