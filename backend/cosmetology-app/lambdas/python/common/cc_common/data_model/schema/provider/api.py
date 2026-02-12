# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
from marshmallow import ValidationError, validates_schema
from marshmallow.fields import Integer, List, Nested, Raw, String
from marshmallow.validate import Length, Range, Regexp

from cc_common.data_model.schema.base_record import ForgivingSchema
from cc_common.data_model.schema.common import CCRequestSchema
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    CompactEligibility,
    Jurisdiction,
    Set,
    SocialSecurityNumber,
)
from cc_common.data_model.schema.license.api import (
    LicenseGeneralResponseSchema,
    LicenseReadPrivateResponseSchema,
)
from cc_common.data_model.schema.privilege.api import (
    PrivilegeGeneralResponseSchema,
    PrivilegePublicResponseSchema,
    PrivilegeReadPrivateResponseSchema,
)

# Keys that indicate cross-index query attempts in OpenSearch DSL
# These are used by terms lookup, more_like_this, and other queries to reference external indices
_CROSS_INDEX_KEYS = frozenset({'index', '_index'})


def _validate_no_cross_index_keys(obj, path: str = 'query') -> None:
    """
    Recursively validate that an object does not contain cross-index lookup keys.

    This function traverses the query structure looking for keys that would indicate
    an attempt to access data from other indices:
    - 'index': Used in terms lookup queries to specify an external index
    - '_index': Used in more_like_this queries to reference documents from other indices

    These keys should never appear in legitimate single-index queries against the
    provider search index.

    :param obj: The object to validate (dict, list, or scalar)
    :param path: The current path in the object for error messages
    :raises ValidationError: If a cross-index key is found
    """
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in _CROSS_INDEX_KEYS:
                raise ValidationError(f"Cross-index queries are not allowed. Found '{key}' at {path}.{key}")
            _validate_no_cross_index_keys(value, path=f'{path}.{key}')
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _validate_no_cross_index_keys(item, path=f'{path}[{i}]')
    # Scalar values (str, int, bool, None) are safe - we only check keys


class ProviderSSNResponseSchema(ForgivingSchema):
    """
    Schema for provider SSN API responses.

    This schema validates the response from the provider SSN endpoint,
    ensuring the SSN is properly formatted.

    Serialization direction:
    Python -> load() -> API
    """

    ssn = SocialSecurityNumber(required=True, allow_none=False)


class ProviderReadPrivateResponseSchema(ForgivingSchema):
    """
    Provider object fields that are sanitized for users with the 'readPrivate' permission.

    This schema is intended to be used to filter from the database in order to remove all fields not defined here.
    It should NEVER be used to load data into the database. Use the ProviderRecordSchema for that.

    This schema should be used by any endpoint that returns provider information to staff users with read private
    permissions (ie the query provider and GET provider endpoints).

    Serialization direction:
    Python -> load() -> API
    """

    providerId = Raw(required=True, allow_none=False)
    type = String(required=True, allow_none=False)

    dateOfUpdate = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseStatus = ActiveInactive(required=True, allow_none=False)
    compactEligibility = CompactEligibility(required=True, allow_none=False)

    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    # This date is determined by the license records uploaded by a state
    # they do not include a timestamp, so we use the Date field type
    dateOfExpiration = Raw(required=True, allow_none=False)

    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)

    privilegeJurisdictions = Set(String, required=False, allow_none=False, load_default=set())
    providerFamGivMid = String(required=False, allow_none=False, validate=Length(2, 400))
    providerDateOfUpdate = Raw(required=False, allow_none=False)
    birthMonthDay = String(required=True, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))

    # these records are present when getting provider information from the GET endpoint
    # so we check for them here and sanitize them if they are present
    licenses = List(Nested(LicenseReadPrivateResponseSchema(), required=False, allow_none=False))
    privileges = List(Nested(PrivilegeReadPrivateResponseSchema(), required=False, allow_none=False))

    # these fields are specific to the read private role
    dateOfBirth = Raw(required=True, allow_none=False)
    ssnLastFour = String(required=False, allow_none=False, validate=Length(equal=4))


class ProviderGeneralResponseSchema(ForgivingSchema):
    """
    Provider object fields that are sanitized for users with the 'readGeneral' permission.

    This schema is intended to be used to filter from the database in order to remove all fields not defined here.
    It should NEVER be used to load data into the database. Use the ProviderRecordSchema for that.

    This schema should be used by any endpoint that returns provider information to staff users (ie the query provider
    and GET provider endpoints).

    Serialization direction:
    Python -> load() -> API
    """

    providerId = Raw(required=True, allow_none=False)
    type = String(required=True, allow_none=False)

    dateOfUpdate = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseStatus = ActiveInactive(required=True, allow_none=False)
    compactEligibility = CompactEligibility(required=True, allow_none=False)

    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))
    # This date is determined by the license records uploaded by a state
    dateOfExpiration = Raw(required=True, allow_none=False)

    jurisdictionUploadedLicenseStatus = ActiveInactive(required=True, allow_none=False)
    jurisdictionUploadedCompactEligibility = CompactEligibility(required=True, allow_none=False)

    privilegeJurisdictions = Set(String, required=False, allow_none=False, load_default=set())
    providerFamGivMid = String(required=False, allow_none=False, validate=Length(2, 400))
    providerDateOfUpdate = Raw(required=False, allow_none=False)
    birthMonthDay = String(required=True, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))

    # these records are present when getting provider information from the GET endpoint
    # so we check for them here and sanitize them if they are present
    licenses = List(Nested(LicenseGeneralResponseSchema(), required=False, allow_none=False))
    privileges = List(Nested(PrivilegeGeneralResponseSchema(), required=False, allow_none=False))


class ProviderPublicResponseSchema(ForgivingSchema):
    """
    Provider object fields that are sanitized for the public lookup endpoints.

    This schema is intended to be used to filter from the database in order to remove all fields not defined here.
    It should NEVER be used to load data into the database. Use the ProviderRecordSchema for that.

    This schema should be used by any endpoint that returns provider information to the public lookup endpoints
    (ie the public query provider and public GET provider endpoints).

    Serialization direction:
    Python -> load() -> API
    """

    providerId = Raw(required=True, allow_none=False)
    type = String(required=True, allow_none=False)

    dateOfUpdate = Raw(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    licenseJurisdiction = Jurisdiction(required=True, allow_none=False)
    licenseStatus = ActiveInactive(required=True, allow_none=False)
    compactEligibility = CompactEligibility(required=True, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    middleName = String(required=False, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    suffix = String(required=False, allow_none=False, validate=Length(1, 100))

    privilegeJurisdictions = Set(String, required=False, allow_none=False, load_default=set())
    # Unlike the internal provider search endpoints used by staff users, which return license data in addition to
    # privilege data for a provider, we only return privilege data for a provider from the public GET provider endpoint
    privileges = List(Nested(PrivilegePublicResponseSchema(), required=False, allow_none=False))
    # Note the lack of `licenses` here: we do not return license data for public endpoints


class QueryProvidersRequestSchema(CCRequestSchema):
    """
    Schema for query providers requests.

    This schema is used to validate incoming requests to both the staff and public query providers API endpoints.
    It corresponds to the V1QueryProvidersRequestModel in the API model.

    Serialization direction:
    API -> load() -> Python
    """

    class QuerySchema(CCRequestSchema):
        """
        Nested schema for the query object within the request.
        """

        providerId = String(required=False, allow_none=False, validate=Length(min=1))
        jurisdiction = Jurisdiction(required=False, allow_none=False)
        givenName = String(required=False, allow_none=False, validate=Length(min=1, max=100))
        familyName = String(required=False, allow_none=False, validate=Length(min=1, max=100))

    class PaginationSchema(ForgivingSchema):
        """
        Nested schema for the pagination object within the request.
        """

        lastKey = String(required=False, allow_none=False, validate=Length(min=1, max=1024))
        pageSize = Integer(required=False, allow_none=False)

    class SortingSchema(ForgivingSchema):
        """
        Nested schema for the sorting object within the request.
        """

        key = String(required=False, allow_none=False)
        direction = String(required=False, allow_none=False)

    query = Nested(QuerySchema, required=True, allow_none=False)
    pagination = Nested(PaginationSchema, required=False, allow_none=False)
    sorting = Nested(SortingSchema, required=False, allow_none=False)


class SearchProvidersRequestSchema(CCRequestSchema):
    """
    Schema for advanced search providers requests.

    This schema is used to validate incoming requests to the advanced search providers API endpoint.
    It accepts an OpenSearch DSL query body for flexible querying of the provider index.

    The request body closely mirrors OpenSearch DSL for pagination using `search_after`.
    See: https://docs.opensearch.org/latest/search-plugins/searching-data/paginate/#the-search_after-parameter

    Serialization direction:
    API -> load() -> Python
    """

    # The OpenSearch query body - we use Raw to allow the full flexibility of OpenSearch queries
    query = Raw(required=True, allow_none=False)

    # Pagination parameters following OpenSearch DSL
    # 'from' is a reserved word in Python, so we use 'from_' with data_key='from'
    from_ = Integer(required=False, allow_none=False, data_key='from', validate=Range(min=0, max=9900))
    size = Integer(required=False, allow_none=False, validate=Range(min=1, max=100))

    # Sort order - required when using search_after pagination
    # Example: [{"providerId": "asc"}, {"dateOfUpdate": "desc"}]
    sort = Raw(required=False, allow_none=False)

    # The search_after parameter for cursor-based pagination
    # This should be the 'sort' values from the last hit of the previous page
    # Example: ["provider-uuid-123", "2024-01-15T10:30:00Z"]
    search_after = Raw(required=False, allow_none=False)

    @validates_schema
    def validate_no_cross_index_queries(self, data, **kwargs):
        """
        Validate that the query does not contain cross-index lookup attempts.

        This is a defense-in-depth security measure to prevent queries that attempt to access
        data from other compact indices. The primary protection is the OpenSearch domain setting
        `rest.action.multi.allow_explicit_index: false`, but this validation provides an
        additional application-layer check.

        Dangerous patterns blocked:
        - Terms lookup with external index: {"terms": {"field": {"index": "other_index", ...}}}
        - More like this with external docs: {"more_like_this": {"like": [{"_index": "other_index"}]}}
        """
        _validate_no_cross_index_keys(data.get('query', {}))
