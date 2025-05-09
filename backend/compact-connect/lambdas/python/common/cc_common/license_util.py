from dataclasses import dataclass

from cc_common.config import config


@dataclass
class LicenseType:
    """Represents a license type with name and abbreviation."""

    name: str
    abbreviation: str


class LicenseUtility:
    """Utility class for working with license types across compacts."""

    @staticmethod
    def get_license_type_by_abbreviation(compact: str, abbreviation: str) -> LicenseType | None:
        """
        Get a license type by its abbreviation within a compact.

        :param compact: The compact code
        :param abbreviation: The license type abbreviation

        :return: LicenseType object if found, None otherwise
        """
        try:
            abbreviations = config.license_type_abbreviations_for_compact(compact)
            for name, abbr in abbreviations.items():
                if abbr.lower() == abbreviation.lower():
                    return LicenseType(name=name, abbreviation=abbr)
            return None
        except KeyError:
            return None
