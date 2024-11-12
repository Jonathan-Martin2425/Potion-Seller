from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
import random

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
    res = 0
    cur = 0
    for t in barrel_types:
        if barrel_types[res] > t and cur != max_potion:
            res = cur
        cur += 1
    return res


@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")


    # what does "OK" do in a Json package/SQL execution
    # "OK" tells the receiver that no error occurred

    barrel_dict = []
    price = 0
    # iterates through each barrel purchased
    for b in barrels_delivered:

        # converts potion type to appropriate barrel_type from the table
        if b.potion_type[0] == 1:
            b_type = 'red'
        elif b.potion_type[1] == 1:
            b_type = 'green'
        elif b.potion_type[2] == 1:
            b_type = 'blue'

        # sets barrel values to be added to both ledgers
        barrel_dict.append({
            "ml": b.quantity * b.ml_per_barrel,
            "type": b_type
        })
        price -= b.price * b.quantity

    # executes inserts into ledgers
    # only the total cost of barrels into the 1s ledger
    # then all the gained mls and their types into the barrel_ledger
    with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text(f"INSERT INTO ledger (gold, customer_name, order_id) VALUES "
                                               f"({price}, 'barrel_lord', {order_id})"))
            connection.execute(sqlalchemy.text(f"INSERT INTO barrel_ledger (type, ml, order_id) VALUES "
                                               f"(:type, :ml, {order_id})"), barrel_dict)

    return []


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    barrel_types = []
    potion_types = []
    with db.engine.begin() as connection:
        gold = connection.execute(sqlalchemy.text("SELECT SUM(gold) AS total_gold FROM ledger")).scalar()

        ml_capacity = connection.execute(sqlalchemy.text("SELECT barrel_capacity FROM global_inventory")).scalar()

        # gets quantity of ml for each type
        t = connection.execute(sqlalchemy.text("SELECT barrel_type, SUM(barrel_ledger.ml) AS total_ml FROM barrels "
                                               "LEFT JOIN barrel_ledger ON type = barrel_type "
                                               "GROUP BY barrel_type "
                                               "ORDER BY barrel_type DESC"))

        total_ml = 0
        for b in t:
            if b.total_ml is None:
                barrel_types.append(0)
            else:
                total_ml += b.total_ml
                barrel_types.append(b.total_ml)

        total_potions = 0
        t = connection.execute(
                sqlalchemy.text("SELECT potion_sku, potion_name, SUM(ledger.quantity) AS total, r, g, b, d FROM potions "
                                "LEFT JOIN ledger ON sku = potion_sku "
                                "WHERE r = 100 OR g = 100 OR b = 100 "
                                "GROUP BY potions.id, potion_sku, potion_name, r, g, b, d "
                                "ORDER BY potions.id ASC"))
        for p in t:
            if p.total is None:
                total = 0
            else:
                total = p.total
            cur_p = (Potion(p.potion_sku, p.potion_name, total, [p.r, p.g, p.b, p.d]))
            total_potions += cur_p.quantity
            potion_types.append(cur_p)

    barrel_skus = [""] * 3
    barrel_skus_total = [0] * 3
    for barrel in wholesale_catalog:
        max_potion = max(potion_types[0].quantity, potion_types[1].quantity, potion_types[2].quantity)
        min_ml = min_barrels(barrel_types, max_potion)
        for i in range(3):
            if barrel.potion_type[i] == 1 and gold >= barrel.price and\
                    (min_ml == i or gold >= barrel.price * 3):
                barrel_skus[i] = barrel.sku
                barrel_skus_total[i] = barrel.ml_per_barrel

                # updates values for deciding what to buy, but doesn't
                # update to database because deliver barrels will do that
                barrel_types[i] += barrel.ml_per_barrel
                gold -= barrel.price
    res = []
    if total_potions < 85:
        random_list = [0, 1, 2]
        random.shuffle(random_list)
        for i in random_list:
            if barrel_skus[i] != "" and total_ml < (ml_capacity + 1) * 10000:
                res.append(barrel_json(barrel_skus[i], 1))
                total_ml += barrel_skus_total[i]
    return res
