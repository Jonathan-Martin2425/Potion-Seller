import random

from fastapi import APIRouter
import sqlalchemy
from src import database as db
import math

router = APIRouter()


# Represents a potion's attributes per row on the potions table
class Potion:
    sku: str
    quantity: int
    type_list: list[int]
    name: str

    def __init__(self, sku: str, name: str, quantity: int, type_list: list[int]):
        self.sku = sku
        self.name = name
        self.quantity = quantity
        self.type_list = type_list

    def __repr__(self):
        return "Sku: " + self.sku + " Name: " + self.name + " quantity: " + str(self.quantity) + " type: " + str(
            self.type_list)


def catalog_json(quantity: int, sku: str, name: str, potion_type: list):
    cur_name = name
    cur_sku = sku
    return {
        "sku": cur_sku,
        "name": cur_name,
        "quantity": quantity,
        "price": 50,
        "potion_type": potion_type,
    }


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    res = []
    with db.engine.begin() as connection:

        # checks quantity of all potion types and adds
        # potions type to catalog if there >0 in the inventory
        potion_types = []
        t = connection.execute(
            sqlalchemy.text("SELECT potion_sku, potion_name, SUM(ledger.quantity) AS total, r, g, b, d FROM potions "
                            "LEFT JOIN ledger ON sku = potion_sku "
                            "GROUP BY potion_sku, potion_name, r, g, b, d "
                            "ORDER BY total ASC")).all()
        for p in t:
            if p.total is not None:
                potion_types.append(Potion(p.potion_sku, p.potion_name, p.total, [p.r, p.g, p.b, p.d]))
            else:
                potion_types.append(Potion(p.potion_sku, p.potion_name, 0, [p.r, p.g, p.b, p.d]))

        # iterates through all potion_types randomly and adds them to the catalog
        random.shuffle(potion_types)
        for p in potion_types:
            if p.quantity > 0:
                res.append(catalog_json(p.quantity, p.sku, p.name, p.type_list))
            if len(res) == 6:
                break
    return res
