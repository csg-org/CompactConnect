"""
License type recognition by jurisdiction for the social-work compact.

Not every license type is recognized by every jurisdiction. When displaying
which privileges are associated with a practitioner, we need to take
into account what type of license they have, and filter the final list of
privileges based on which states recognize that license type.

This file defines the mapping for each jurisdiction to the license types
it recognizes.
"""

from cc_common.exceptions import CCInternalException

# SOCW License type abbreviations — must match values in cdk.json
LCSW = 'lcsw'  # licensed clinical social worker
LMSW = 'lmsw'  # licensed master social worker
LBSW = 'lbsw'  # licensed bachelor social worker

_LICENSE_TYPE_JURISDICTION_MAPPING: dict[str, dict[str, set[str]]] = {
    'socw': {
        'al': {LCSW, LMSW, LBSW},
        'ak': {LCSW, LMSW, LBSW},
        'az': {LCSW, LMSW, LBSW},
        'ar': {LCSW, LMSW, LBSW},
        'ca': {LCSW},
        'co': {LCSW, LMSW},
        'ct': {LCSW, LMSW},
        'de': {LCSW, LMSW, LBSW},
        'dc': {LCSW, LMSW, LBSW},
        'fl': {LCSW, LMSW},
        'ga': {LCSW, LMSW},
        'gu': {LCSW, LMSW, LBSW},
        'hi': [LCSW, LMSW, LBSW],
        'id': {LCSW, LMSW, LBSW},
        'il': {LCSW, LMSW, LBSW},
        'in': {LCSW, LMSW, LBSW},
        'ia': {LCSW, LMSW, LBSW},
        'ks': {LCSW, LMSW, LBSW},
        'ky': {LCSW, LMSW, LBSW},
        'la': {LCSW, LMSW, LBSW},
        'me': {LCSW, LMSW, LBSW},
        'md': {LCSW, LMSW, LBSW},
        'ma': {LCSW, LMSW, LBSW},
        'mi': {LCSW, LBSW},
        'mn': {LCSW, LMSW, LBSW},
        'ms': {LCSW, LMSW, LBSW},
        'mo': {LCSW, LMSW, LBSW},
        'mt': {LCSW, LMSW, LBSW},
        'ne': {LCSW, LMSW, LBSW},
        'nv': {LCSW, LMSW, LBSW},
        'nh': {LCSW, LBSW},
        'nj': {LCSW, LMSW, LBSW},
        'nm': {LCSW, LMSW, LBSW},
        'ny': {LCSW, LMSW},
        'nc': {LCSW, LMSW, LBSW},
        'nd': {LCSW, LMSW, LBSW},
        'mp': {LCSW, LMSW, LBSW},
        'oh': {LCSW, LMSW, LBSW},
        'ok': {LCSW, LMSW, LBSW},
        'or': {LCSW, LMSW, LBSW},
        'pa': {LCSW, LMSW, LBSW},
        'ri': {LCSW, LMSW},
        'sc': {LCSW, LMSW, LBSW},
        'sd': {LCSW, LMSW, LBSW},
        'tn': {LCSW, LMSW, LBSW},
        'tx': {LCSW, LMSW, LBSW},
        'ut': {LCSW, LMSW, LBSW},
        'vt': {LCSW, LMSW},
        'vi': {LCSW, LMSW, LBSW},
        'va': {LCSW, LMSW, LBSW},
        'wa': {LCSW, LMSW},
        'wv': {LCSW, LMSW, LBSW},
        'wi': {LCSW, LMSW, LBSW},
        'wy': {LCSW, LBSW},

    },
}

class LicenseRecognitionUtil:
    """Utility for checking whether a license type is recognized in a jurisdiction."""

    @staticmethod
    def license_type_is_recognized_in_jurisdiction(
        compact: str,
        jurisdiction: str,
        license_type_abbreviation: str,
    ) -> bool:
        """
        Return whether the given license type is recognized in the jurisdiction.

        :param compact: The compact abbreviation
        :param jurisdiction: The jurisdiction postal abbreviation
        :param license_type_abbreviation: The license type abbreviation
        :return: True if the license type is recognized in the jurisdiction
        :raises CCInternalException: If the compact or jurisdiction is not configured
        """
        compact_key = compact.lower()
        jurisdiction_key = jurisdiction.lower()

        compact_jurisdictions = _LICENSE_TYPE_JURISDICTION_MAPPING.get(compact_key)
        if compact_jurisdictions is None:
            raise CCInternalException(f'No license type recognition mapping for compact: {compact}')

        recognized = compact_jurisdictions.get(jurisdiction_key)
        if recognized is None:
            raise CCInternalException(
                f'No license type recognition mapping for jurisdiction {jurisdiction} in compact {compact}'
            )
        return license_type_abbreviation.lower() in recognized
