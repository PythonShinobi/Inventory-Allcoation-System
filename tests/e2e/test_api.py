import pytest
import requests

import config
from tests.random_refs import (
    random_batchref,
    random_orderid,
    random_sku,
)


@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_201_and_allocated_batch(add_stock):
    sku = random_sku()
    other_sku = random_sku("other")

    early_batch = random_batchref(1)
    later_batch = random_batchref(2)
    other_batch = random_batchref(3)

    add_stock([
        (later_batch, sku, 100, "2011-01-02"),
        (early_batch, sku, 100, "2011-01-01"),
        (other_batch, other_sku, 100, None),
    ])

    response = requests.post(
        f"{config.get_api_url()}/allocate",
        json={
            "orderid": random_orderid(),
            "sku": sku,
            "qty": 3,
        },
    )

    assert response.status_code == 201
    assert response.json()["batchref"] == early_batch


@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message():
    unknown_sku = random_sku()
    orderid = random_orderid()

    response = requests.post(
        f"{config.get_api_url()}/allocate",
        json={
            "orderid": orderid,
            "sku": unknown_sku,
            "qty": 20,
        },
    )

    assert response.status_code == 400
    assert response.json()["message"] == (
        f"Invalid sku {unknown_sku}"
    )