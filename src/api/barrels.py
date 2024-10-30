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


# given the parameters for the correct API response
# returns the correct json format
def barrel_json(item_sku: str, quantity: int):
    return {"sku": item_sku,
            "quantity": quantity}


# takes in a list and returns the min index
# used for finding min ml of all barrel types
def min_barrels(barrel_types: list, max_potion: int) -> int:
    m = 0
    cur = 0
    for t in barrel_types:
        if barrel_types[m] > t and cur != max_potion:
            m = cur
        cur += 1
    return m


@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")

    barrels_dict = [{
        "ml": 0,
        "color": 'red'
    },
        {
            "ml": 0,
            "color": 'green'
        },
        {
            "ml": 0,
            "color": 'blue'
        }]

    for b in barrels_delivered:
        for i in range(3):
            if b.potion_type[i] == 1:
                barrels_dict[i]["ml"] += b.ml_per_barrel

    # what does "OK" do in a Json package/SQL execution
    # "OK" tells the receiver that no error occurred

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(f"UPDATE barrels SET ml = ml + :ml "
                                           f"WHERE barrel_type = :color"), barrels_dict)

    return []


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    barrel_types = []
    potion_types = []
    with db.engine.begin() as connection:
        gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

        # gets quantity of ml for each type
        t = connection.execute(sqlalchemy.text("SELECT ml FROM barrels ORDER BY barrel_type DESC"))
        for b in t:
            barrel_types.append(b.ml)

        total_potions = 0
        for t in connection.execute(
                sqlalchemy.text("SELECT potion_sku, potion_name, quantity, R, G, B, D FROM potions "
                                "WHERE r = 100 OR g = 100 OR b = 100 ORDER BY id ASC")):
            p = (Potion(t.potion_sku, t.potion_name, t.quantity, [t.r, t.g, t.b, t.d]))
            total_potions += p.quantity
            potion_types.append(p)

    barrel_skus = [""] * 3
    for barrel in wholesale_catalog:
        max_potion = max(potion_types[0].quantity, potion_types[1].quantity, potion_types[2].quantity)
        min_ml = min_barrels(barrel_types, max_potion)
        for i in range(3):
            if barrel.potion_type[i] == 1 and gold >= barrel.price and\
                    (min_ml == i or gold >= barrel.price * 3):
                barrel_skus[i] = barrel.sku

                # updates values for deciding what to buy, but doesn't
                # update to database because deliver barrels will do that
                barrel_types[i] += barrel.ml_per_barrel
                gold -= barrel.price
    res = []

    if total_potions < 85:
        if barrel_skus[0] != "":
            res.append(barrel_json(barrel_skus[0], 1))
        if barrel_skus[1] != "":
            res.append(barrel_json(barrel_skus[1], 1))
        if barrel_skus[2] != "":
            res.append(barrel_json(barrel_skus[2], 1))
    return res
