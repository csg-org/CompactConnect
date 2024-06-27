from csv import DictReader
from io import TextIOBase
from typing import Generator

from schema import LicensePostSchema


class LicenseCSVReader:
    def __init__(self):
        self.schema = LicensePostSchema()

    def _licenses(self, stream: TextIOBase) -> Generator[dict, None, None]:
        reader = DictReader(stream, restkey='invalid', dialect='excel', strict=True)
        for license_row in reader:
            # Drop fields that are blank
            drop_fields = [k for k, v in license_row.items() if v == '']
            for k in drop_fields:
                del license_row[k]

            yield license_row

    def validated_licenses(self, stream: TextIOBase) -> Generator[dict, None, None]:
        for license_row in self._licenses(stream):
            yield self.schema.load(license_row)
