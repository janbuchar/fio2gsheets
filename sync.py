from dataclasses import dataclass
from datetime import datetime, timedelta, date
from decimal import Decimal
import os

import gspread
import pytz
import requests


def excel_date(value: date) -> int:
    return (value - date(1899, 12, 30)).days


@dataclass(frozen=True)
class Row:
    id: int
    date: date
    account: str
    bank: str
    amount: Decimal
    message: str
    comment: str


def read_transactions(transactions):
    for row in transactions["accountStatement"]["transactionList"]["transaction"]:
        yield Row(
            id=row["column22"]["value"],
            date=datetime.strptime(row["column0"]["value"], "%Y-%m-%d%z").date(),
            account=row["column2"]["value"] if row["column2"] is not None else "",
            bank=row["column3"]["value"] if row["column3"] is not None else "",
            amount=Decimal(row["column1"]["value"]),
            message=row["column16"]["value"] if row["column16"] is not None else "",
            comment=row["column25"]["value"] if row["column25"] is not None else "",
        )


def fetch_transactions():
    token = os.environ.get("FIO_TOKEN")
    to_date = datetime.now(pytz.timezone("Europe/Prague"))
    from_date = to_date - timedelta(days=90)
    response = requests.get(
        f"https://fioapi.fio.cz/ib_api/rest/periods/{token}/{from_date:%Y-%m-%d}/{to_date:%Y-%m-%d}/transactions.json"
    )
    response.raise_for_status()
    return response.json()


def push_transactions(transactions):
    client = gspread.service_account(filename=os.path.abspath("./service_account.json"))
    doc = client.open(os.environ.get("SHEET_NAME"))
    sheet = doc.worksheet("Data")
    ids = sheet.col_values(1)
    sheet.clear_basic_filter()

    sheet.append_rows(
        [
            [
                str(row.id),
                str(excel_date(row.date)),
                row.account,
                row.bank,
                str(row.amount),
                row.message,
                row.comment,
            ]
            for row in transactions
            if str(row.id) not in ids
        ],
        value_input_option="USER_ENTERED",
    )
    sheet.format(f"B2:B{sheet.row_count}", {"numberFormat": {"type": "DATE"}})

    # Reconfigure basic filter
    doc.batch_update(
        {
            "requests": [
                {
                    "setBasicFilter": {
                        "filter": {
                            "range": {"sheetId": sheet.id},
                            "sortSpecs": [
                                {"dimensionIndex": 1, "sortOrder": "DESCENDING"}
                            ],
                        }
                    }
                }
            ]
        }
    )


def main():
    response = fetch_transactions()
    transactions = [*read_transactions(response)]
    push_transactions(transactions)


if __name__ == "__main__":
    main()
