from csv import DictReader
from io import TextIOBase
from typing import Generator

from data_model.schema.license import LicensePostSchema


class LicenseCSVReader:
    def __init__(self):
        self.schema = LicensePostSchema()

    def licenses(self, stream: TextIOBase) -> Generator[dict, None, None]:
        reader = DictReader(stream, restkey='invalid', dialect='excel', strict=True)
        for license_row in reader:
            # Drop fields that are blank
            drop_fields = [k for k, v in license_row.items() if v == '']
            for k in drop_fields:
                del license_row[k]

            yield license_row
