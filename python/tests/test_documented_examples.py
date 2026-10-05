"""The documented examples (contract/documented_examples.json) are what the SDK really sends.

The same file is posted against the API golden suite
(yo-facturo_api tests/integration/critical_flows/public_api_golden/test_public_api_documented_examples.py),
so "the SDK call produces this body" + "the API accepts this body" together pin the documented
examples (findings F5, F9, F12).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_FILE = Path(__file__).resolve().parents[2] / "contract" / "documented_examples.json"
_ALL = json.loads(_FILE.read_text(encoding="utf-8"))
SDK_EXAMPLES = {k: v for k, v in _ALL.items() if not k.startswith("_") and "sdk" in v}

_PATHS = {
    "invoice": "/bill/receipts/invoice/",
    "invoice_customer": "/bill/receipts/invoice/customer/",
    "credit_note": "/bill/receipts/credit-note/",
    "debit_note": "/bill/receipts/debit-note/",
}


def test_every_sdk_example_is_covered():
    assert set(SDK_EXAMPLES) >= {
        "invoice_minimal_final_price", "invoice_to_stored_customer",
        "debit_note_items_net_with_total", "credit_note_total", "credit_note_by_lines", "credit_note_by_amount", "credit_note_by_percentage",
    }


@pytest.mark.parametrize("name", sorted(SDK_EXAMPLES))
def test_sdk_call_produces_the_documented_body(make_client, name):
    example = SDK_EXAMPLES[name]
    client, transport = make_client([(200, {}, {"success": True, "data": {}})])
    resource_name, method_name = example["sdk"]["call"].split(".")
    getattr(getattr(client, resource_name), method_name)(*example["sdk"]["args"], **example["sdk"]["kwargs"])
    call = transport.last_call
    assert call["url"].endswith(_PATHS[example["endpoint"]])
    assert call["body"] == example["body"]
