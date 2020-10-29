#!/usr/bin/env python3
import argparse
import csv
import datetime
import pathlib
import collections
import logging
from operator import itemgetter
from typing import Tuple, Union, List, Iterator, Optional

_tax_tuple = collections.namedtuple("TaxTuple", ["tax", "currency"])
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
_stream = logging.StreamHandler()
_stream.setLevel(logging.DEBUG)
_formatter = logging.Formatter("{name} - {asctime} [{levelname}]: {message}", style="{")
_stream.setFormatter(_formatter)
_logger.addHandler(_stream)


def extract_company(vtb_comment: str) -> str:
    # company name here is after the following keyword
    # "Дивиденды по ценным бумагам". The company name would lay
    # between the prefix above and the next description that starts
    # with "Дивиденды"
    def extract_after_prefix_1(comment: str) -> str:
        return comment[len(prefix_1):comment.rfind(company_name_end)].strip()

    def extract_after_prefix_2(comment: str) -> str:
        return comment[len(prefix_2):comment.rfind(company_name_end)].strip()

    prefix_1 = "Дивиденды по ценным бумагам"
    prefix_2 = "Дивиденды по акциям"
    company_name_end = "Дивиденды"
    assert vtb_comment.startswith(prefix_1) or vtb_comment.startswith(prefix_2)

    if vtb_comment.startswith(prefix_1):
        return extract_after_prefix_1(vtb_comment)
    else:
        return extract_after_prefix_2(vtb_comment)


def extract_tax(vtb_comment: str) -> Optional[_tax_tuple]:
    if "Налог не удерживается" in vtb_comment:
        return None

    index = vtb_comment.find("налог")
    assert index >= 0, vtb_comment

    _, tax, currency = vtb_comment[index:].rstrip(".").split()
    return _tax_tuple(float(tax), currency)


def filter_dividends(reader: csv.DictReader) -> Iterator:
    return filter(
        lambda comment: comment["коммент"].startswith("Дивиденды") and
        "Налог не удерживается" not in comment["коммент"], reader
    )


def basic_parser(
    filename: Union[str, pathlib.Path]
) -> List[Tuple[datetime.datetime, float, str, float, str]]:
    file_to_use = pathlib.Path(filename)
    results = []

    with file_to_use.open() as f:
        reader = csv.DictReader(f, delimiter=";")

        for row in filter_dividends(reader):
            date = datetime.datetime.strptime(row["дата"], "%d.%M.%Y")
            total = float(row["сумма"].replace(" ", "").replace(",", "."))
            company = extract_company(row["коммент"])
            tax = extract_tax(row["коммент"])

            if tax is not None:
                results.append((date, total, company, tax.tax, tax.currency))

        return sorted(results, key=itemgetter(0))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "csvfile", type=str, help="VTB Broker Account operations CSV document"
    )
    args = parser.parse_args()
    result = basic_parser(args.csvfile)

    with open("output.csv", "w", newline="") as out:
        output_csv = csv.writer(out)
        output_csv.writerow(["Дата", "Дивиденды", "Компания", "Налог"])

        for e in result:
            output_csv.writerow((e[0].strftime("%d.%M.%Y"), e[1], e[2], f"{e[3]}"))
            _logger.debug(
                "\n{}\n{}\n{}\n{}\n{}\n{}".format(
                    "=" * 70, e[0].strftime("%d.%M.%Y"), f"Дивиденды: {e[1]}",
                    f"Компания: {e[2]}", f"Налог: {e[3]} {e[4]}", "=" * 70
                )
            )
