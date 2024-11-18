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
        gold, potions = connection.execute(sqlalchemy.text("SELECT SUM(gold) AS total_gold, "
                                                               "SUM(quantity) "
                                                               "FROM ledger")).one()

        ml = connection.execute(sqlalchemy.text("SELECT SUM(ml) AS total_ml FROM barrel_ledger")).scalar()
        return {"gold": gold, "number_of_potions": potions, "ml_in_barrels": ml}


# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    with db.engine.begin() as connection:

        # gets values to determine plan
        gold = connection.execute(sqlalchemy.text("SELECT SUM(gold) AS total_gold FROM ledger")).scalar()

        values = connection.execute(sqlalchemy.text("SELECT potion_capacity, barrel_capacity FROM global_inventory")).one()
        p_capacity = values.potion_capacity
        b_capacity = values.barrel_capacity

        # manually adds capacity and sets them and price
        # if there is enough gold
        if gold > 5500 and p_capacity < 2:
            new_pCapacity = (2 - p_capacity)
            new_bCapacity = (2 - b_capacity)
        elif gold > 2750 and p_capacity < 1:
            new_pCapacity = 1
            new_bCapacity = 1
        else:
            new_pCapacity = 0
            new_bCapacity = 0

        # updates global_inventory regardless if a change occurred
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
    price = -(capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000
    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(f"INSERT INTO ledger (gold, customer_name, order_id) VALUES ({price}, 'Admin', {order_id})"))
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET "
                                           f"potion_capacity = potion_capacity + {capacity_purchase.potion_capacity},"
                                           f"barrel_capacity = barrel_capacity + {capacity_purchase.ml_capacity}"))
    return "OK"
