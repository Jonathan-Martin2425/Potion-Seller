from fastapi import APIRouter
import sqlalchemy
from src import database as db
import math

router = APIRouter()


def catalog_json(quantity: int, sku: str, name: str, potion_type: list):
    cur_name = name
    cur_sku = sku
    return {
        "sku": cur_sku,
        "name": cur_name,
        "quantity": quantity,
        "price": 100,
        "potion_type": potion_type,
    }


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    res = []
    potion_skus = ["RED_POTION", "GREEN_POTION", "BLUE_POTION"]
    potion_names = ["red potion", "green potion", "blue potion"]
    with db.engine.begin() as connection:

        # checks quantity of all potion types and adds
        # potions type to catalog if there >0 in the inventory
        potion_types = []
        for t in connection.execute(sqlalchemy.text("SELECT quantity FROM potions ORDER BY id ASC")):
            potion_types.append(t[0])
        for i in range(3):
            if potion_types[i] > 0:
                cur_potion_type = [0] * 4
                cur_potion_type[i] += 100
                res.append(catalog_json(potion_types[i], potion_skus[i], potion_names[i], cur_potion_type))

    return res
