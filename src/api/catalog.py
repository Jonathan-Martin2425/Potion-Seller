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
        "price": 100,
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
        for t in connection.execute(
                sqlalchemy.text("SELECT potion_sku, potion_name, quantity, R, G, B, D FROM potions ORDER BY id ASC")):
            p = (Potion(t[0], t[1], t[2], [t[3], t[4], t[5], t[6]]))
            potion_types.append(p)
        for i in range(len(potion_types)):
            if potion_types[i].quantity > 0:
                res.append(catalog_json(potion_types[i].quantity, potion_types[i].sku,
                                        potion_types[i].name, potion_types[i].type_list))

    return res
