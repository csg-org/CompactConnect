from collections.abc import Generator
from csv import DictReader
from io import TextIOBase

from cc_common.data_model.schema.license.api import LicensePostRequestSchema


class LicenseCSVReader:
    def __init__(self):
        self.schema = LicensePostRequestSchema()

    def licenses(self, stream: TextIOBase) -> Generator[dict, None, None]:
        reader = DictReader(stream, restkey='invalid', dialect='excel', strict=True)
        for license_row in reader:
            # Drop fields that are blank
            drop_fields = [k for k, v in license_row.items() if v == '']
            for k in drop_fields:
                del license_row[k]

            yield license_row
