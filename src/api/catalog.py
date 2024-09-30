from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar()

    if potions > 0:
        return [
                {
                    "sku": "GREEN_POTION",
                    "name": "green potion",
                    "quantity": 1,
                    "price": 20,
                    "potion_type": [0, 100, 0, 0],
                }
            ]
    else:
        return "OK"
