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
        Retrieves a LicenseType by abbreviation for a given compact.
        
        Searches for a license type matching the specified abbreviation (case-insensitive) within the provided compact. Returns the corresponding LicenseType if found, or None if not found or if the compact is unrecognized.
        """
        try:
            abbreviations = config.license_type_abbreviations_for_compact(compact)
            for name, abbr in abbreviations.items():
                if abbr.lower() == abbreviation.lower():
                    return LicenseType(name=name, abbreviation=abbr)
            return None
        except KeyError:
            return None

    @staticmethod
    def get_valid_license_type_abbreviations(compact: str) -> set[str]:
        """
        Returns the set of valid license type abbreviations for the specified compact.
        
        Args:
        	compact: The code identifying the compact.
        
        Returns:
        	A set containing all valid license type abbreviations for the given compact.
        """
        license_types = config.license_types_for_compact(compact)
        return {config.license_type_abbreviations[compact][license_type] for license_type in license_types}

    @staticmethod
    def find_invalid_license_type_abbreviations(compact: str, abbreviations: list[str]) -> list[str]:
        """
        Returns a list of license type abbreviations that are not valid for the specified compact.
        
        Args:
        	compact: The compact code to validate against.
        	abbreviations: List of license type abbreviations to check.
        
        Returns:
        	A list of abbreviations from the input that are not valid for the given compact. Returns an empty list if all are valid.
        """
        valid_abbreviations = LicenseUtility.get_valid_license_type_abbreviations(compact)

        return [abbr for abbr in abbreviations if abbr not in valid_abbreviations]
