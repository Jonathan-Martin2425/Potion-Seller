from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    res = []
    with db.engine.begin() as connection:

        # checks quantity of all potion types and adds
        # potions type to catalog if there >0 in the inventory
        if connection.execute(sqlalchemy.text("SELECT quantity FROM potions WHERE potion_type= 'red'")).scalar() > 0:
            res.append({
                    "sku": "RED_POTION",
                    "name": "red potion",
                    "quantity": 1,
                    "price": 40,
                    "potion_type": [100, 0, 0, 0],
                })
        if connection.execute(sqlalchemy.text("SELECT quantity FROM potions WHERE potion_type= 'green'")).scalar() > 0:
            res.append({
                    "sku": "GREEN_POTION",
                    "name": "green potion",
                    "quantity": 1,
                    "price": 40,
                    "potion_type": [0, 100, 0, 0],
                })
        if connection.execute(sqlalchemy.text("SELECT quantity FROM potions WHERE potion_type= 'blue'")).scalar() > 0:
            res.append({
                    "sku": "BLUE_POTION",
                    "name": "blue potion",
                    "quantity": 1,
                    "price": 40,
                    "potion_type": [0, 0, 100, 0],
                })

    return res
