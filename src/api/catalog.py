from fastapi import APIRouter
import sqlalchemy
from src import database as db
import math

router = APIRouter()


def catalog_json(sale_type: str, quantity: int, sku: str, name: str, potion_type: list):
    multiplier = 1
    cur_name = name
    cur_sku = sku
    if sale_type == "single":
        cur_quantity = 1
    elif sale_type == 'bulk':
        cur_quantity = quantity
        cur_name += " bulk"
        cur_sku += "_BULK"
        if cur_quantity >= 5:
            multiplier = math.floor(multiplier * cur_quantity * 0.9)
        else:
            multiplier = multiplier * cur_quantity
    return {
        "sku": cur_sku,
        "name": cur_name,
        "quantity": cur_quantity,
        "price": 40 * multiplier,
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
                res.append(catalog_json("single", potion_types[i], potion_skus[i], potion_names[i], cur_potion_type))
                if potion_types[i] > 1:
                    res.append(catalog_json("bulk", potion_types[i], potion_skus[i], potion_names[i], cur_potion_type))
    return res
