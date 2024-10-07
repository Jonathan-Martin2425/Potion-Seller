from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)


class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]  # in the format[0-1, 0-1, 0-1, 0-1] representing R,G, B, dark
    price: int

    quantity: int


# given the parameters for the correct API response
# returns the correct json format
def potion_json(item_sku: str, quantity: int):
    return {"sku": item_sku,
            "quantity": quantity}


#takes in a list and returns the min index
#used for finding min ml of all barrel types
def min_barrels(barrel_types: list) -> int:
    m = 0
    cur = 0
    for t in barrel_types:
        if barrel_types[m] > t:
            m = cur
        cur += 1
    return m


@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    barrel_types = []
    with db.engine.begin() as connection:
        ml = connection.execute(sqlalchemy.text("SELECT ml FROM global_inventory")).scalar()
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

        # gets quantity of ml for each type
        barrel_types.append(
            connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'red'")).scalar())
        barrel_types.append(
            connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'green'")).scalar())
        barrel_types.append(
            connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'blue'")).scalar())

    for b in barrels_delivered:
        for i in range(3):
            if b.potion_type[i] == 1:
                barrel_types[i] += b.ml_per_barrel
                ml += b.ml_per_barrel
                gold -= b.price

    # what does "OK" do in a Json package/SQL excecution
    # "OK" tells the reciever that no error occurred

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET ml = {ml}, gold = {gold} WHERE id= 1"))
        connection.execute(sqlalchemy.text(f"UPDATE barrels SET ml = {barrel_types[0]} WHERE barrel_type= 'red'"))
        connection.execute(sqlalchemy.text(f"UPDATE barrels SET ml = {barrel_types[1]} WHERE barrel_type= 'green'"))
        connection.execute(sqlalchemy.text(f"UPDATE barrels SET ml = {barrel_types[2]} WHERE barrel_type= 'blue'"))

    return []


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    barrel_types = []
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("SELECT potions FROM global_inventory")).scalar()
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()
        # gets quantity of ml for each type
        barrel_types.append(
            connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'red'")).scalar())
        barrel_types.append(
            connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'green'")).scalar())
        barrel_types.append(
            connection.execute(sqlalchemy.text("SELECT ml FROM barrels WHERE barrel_type= 'blue'")).scalar())

    potion_skus = [""] * 3
    for barrel in wholesale_catalog:
        min_ml = min_barrels(barrel_types)
        for i in range(3):
            if barrel.potion_type[i] == 1 and gold >= barrel.price and\
                    (min_ml == i or gold >= barrel.price * 2):
                potion_skus[i] = barrel.sku
                barrel_types[i] += barrel.ml_per_barrel
                gold -= barrel.price
    res = []

    if potions <= 82:
        if potion_skus[0] != "":
            res.append(potion_json(potion_skus[0], 1))
        if potion_skus[1] != "":
            res.append(potion_json(potion_skus[1], 1))
        if potion_skus[2] != "":
            res.append(potion_json(potion_skus[2], 1))
    return res
