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


@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    with db.engine.begin() as connection:
        greenMl = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar()
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

    for b in barrels_delivered:
        if b.potion_type[1] == 1:
            greenMl += b.ml_per_barrel
            gold -= b.price

    # what does "OK" do in a Json package/SQL excecution
    # "OK" tells the reciever that no error occurred

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_ml = {greenMl} WHERE id= 1"))
        result = connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {gold} WHERE id= 1"))
    return []


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar()
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

    green_type = [0, 1, 0, 0]
    green_potion_sku = ""
    for barrel in wholesale_catalog:
        if barrel.potion_type == green_type and barrel.price <= gold:
            green_potion_sku = barrel.sku

    if potions <= 10 and green_potion_sku != "":
        return [
            {
                "sku": green_potion_sku,
                "quantity": 1,
            }
        ]
    else:
        return []
