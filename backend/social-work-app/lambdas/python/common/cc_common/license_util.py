from dataclasses import dataclass

from cc_common.config import config, logger
from cc_common.exceptions import CCInvalidRequestException


@dataclass
class LicenseType:
    """Represents a license type with name and abbreviation."""

    name: str
    abbreviation: str


class LicenseUtility:
    """Utility class for working with license types across compacts."""

    @staticmethod
    def get_license_type_by_abbreviation(compact: str, abbreviation: str) -> LicenseType:
        """
        Get a license type by its abbreviation within a compact.

        :param compact: The compact code
        :param abbreviation: The license type abbreviation

        :return: LicenseType object
        """
        try:
            abbreviations = config.license_type_abbreviations_for_compact(compact)
            for name, abbr in abbreviations.items():
                if abbr.lower() == abbreviation.lower():
                    return LicenseType(name=name, abbreviation=abbr)
            raise CCInvalidRequestException(f'Invalid license type abbreviation: {abbreviation}')
        except KeyError as e:
            logger.error('Invalid license type abbreviation provided.', exc_info=e)
            raise CCInvalidRequestException(f'Invalid license type abbreviation: {abbreviation}') from e

    @staticmethod
    def get_license_type_by_name(compact: str, license_type_name: str) -> LicenseType:
        """
        Get a license type by its full name within a compact, matched case-insensitively.

        This is the shared source of truth for validating a license type *name* (as opposed to an
        abbreviation, see get_license_type_by_abbreviation) against a compact's configured license types.
        Returning the canonically-cased LicenseType (rather than just validating) lets callers normalize
        user input to the exact casing configured for the compact, instead of assuming a particular casing
        convention (e.g. lower-casing) happens to match what was persisted.

        :param compact: The compact code
        :param license_type_name: The license type name to look up (case-insensitive)

        :return: LicenseType object
        :raises CCInvalidRequestException: If the license type name is not configured for the compact
        """
        try:
            abbreviations = config.license_type_abbreviations_for_compact(compact)
            for name, abbr in abbreviations.items():
                if name.lower() == license_type_name.lower():
                    return LicenseType(name=name, abbreviation=abbr)
            raise CCInvalidRequestException(f'Invalid license type: {license_type_name}')
        except KeyError as e:
            logger.error('Invalid license type provided.', exc_info=e)
            raise CCInvalidRequestException(f'Invalid license type: {license_type_name}') from e

    @staticmethod
    def get_valid_license_type_abbreviations(compact: str) -> set[str]:
        """
        Get all valid license type abbreviations for a compact.

        :param compact: The compact code
        :return: Set of valid license type abbreviations
        """
        license_types = config.license_types_for_compact(compact)
        return {config.license_type_abbreviations[compact][license_type] for license_type in license_types}

    @staticmethod
    def find_invalid_license_type_abbreviations(compact: str, abbreviations: list[str]) -> list[str]:
        """
        Check if the provided license type abbreviations are valid for the given compact.

        :param compact: The compact code
        :param abbreviations: List of license type abbreviations to validate
        :return: List of invalid license type abbreviations, empty if all are valid
        """
        valid_abbreviations = LicenseUtility.get_valid_license_type_abbreviations(compact)

        return [abbr for abbr in abbreviations if abbr not in valid_abbreviations]
