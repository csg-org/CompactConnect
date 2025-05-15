class CompactConfigUtility:
    """Utility class for compact and jurisdiction configuration mappings."""

    # Mapping of compact abbreviations to full names
    COMPACT_NAME_MAPPING: dict[str, str] = {
        'coun': 'Counseling',
        'octp': 'Occupational Therapy',
        'aslp': 'Audiology and Speech Language Pathology',
    }

    # Mapping of jurisdiction postal abbreviations to full state names
    JURISDICTION_NAME_MAPPING: dict[str, str] = {
        'al': 'Alabama',
        'ak': 'Alaska',
        'az': 'Arizona',
        'ar': 'Arkansas',
        'ca': 'California',
        'co': 'Colorado',
        'ct': 'Connecticut',
        'de': 'Delaware',
        'fl': 'Florida',
        'ga': 'Georgia',
        'hi': 'Hawaii',
        'id': 'Idaho',
        'il': 'Illinois',
        'in': 'Indiana',
        'ia': 'Iowa',
        'ks': 'Kansas',
        'ky': 'Kentucky',
        'la': 'Louisiana',
        'me': 'Maine',
        'md': 'Maryland',
        'ma': 'Massachusetts',
        'mi': 'Michigan',
        'mn': 'Minnesota',
        'ms': 'Mississippi',
        'mo': 'Missouri',
        'mt': 'Montana',
        'ne': 'Nebraska',
        'nv': 'Nevada',
        'nh': 'New Hampshire',
        'nj': 'New Jersey',
        'nm': 'New Mexico',
        'ny': 'New York',
        'nc': 'North Carolina',
        'nd': 'North Dakota',
        'oh': 'Ohio',
        'ok': 'Oklahoma',
        'or': 'Oregon',
        'pa': 'Pennsylvania',
        'ri': 'Rhode Island',
        'sc': 'South Carolina',
        'sd': 'South Dakota',
        'tn': 'Tennessee',
        'tx': 'Texas',
        'ut': 'Utah',
        'vt': 'Vermont',
        'va': 'Virginia',
        'wa': 'Washington',
        'wv': 'West Virginia',
        'wi': 'Wisconsin',
        'wy': 'Wyoming',
        'dc': 'District of Columbia',
    }

    @classmethod
    def get_compact_name(cls, compact_abbr: str) -> str | None:
        """
        Returns the full compact name corresponding to a given abbreviation.
        
        Args:
        	compact_abbr: The compact abbreviation to look up.
        
        Returns:
        	The full compact name if found; otherwise, None.
        """
        return cls.COMPACT_NAME_MAPPING.get(compact_abbr.lower())

    @classmethod
    def get_jurisdiction_name(cls, postal_abbr: str) -> str | None:
        """
        Returns the full jurisdiction name for a given postal abbreviation.
        
        Args:
            postal_abbr: The postal abbreviation of a U.S. state or district.
        
        Returns:
            The full state or district name if found; otherwise, None.
        """
        return cls.JURISDICTION_NAME_MAPPING.get(postal_abbr.lower())
