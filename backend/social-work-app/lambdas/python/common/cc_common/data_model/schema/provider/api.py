# ruff: noqa: N801, N815, ARG002  invalid-name unused-argument
import re

from marshmallow import ValidationError, pre_load
from marshmallow.fields import Dict, Integer, List, Nested, Raw, String
from marshmallow.validate import Length, OneOf, Range, Regexp

from cc_common.data_model.schema.adverse_action.api import AdverseActionGeneralResponseSchema
from cc_common.data_model.schema.base_record import ForgivingSchema, StrictSchema
from cc_common.data_model.schema.common import CUID_PATTERN, CCRequestSchema
from cc_common.data_model.schema.fields import (
    ActiveInactive,
    Compact,
    CompactEligibility,
    Jurisdiction,
    LicenseScopeField,
    PublicCompactIdentifierField,
)
from cc_common.data_model.schema.license.api import (
    LicenseGeneralResponseSchema,
    LicenseOpenSearchDocumentSchema,
    LicensePublicResponseSchema,
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


# Maximum nesting depth accepted in a caller-supplied query. The deepest query the frontend can
# build is 13 levels (the encumbrance-date condition: bool > should > nested > query > nested >
# query > range > field > bound), so this leaves room for the UI to grow while staying well clear
# of the point where recursing through the schema would exhaust the Python stack and surface as an
# unhandled 500 instead of a 400.
_MAX_QUERY_DEPTH = 20


def _validate_query_depth(query) -> None:
    """
    Validate that a caller-supplied query is not nested beyond _MAX_QUERY_DEPTH.

    Walked iteratively rather than recursively: this guard has to be able to measure a query that
    is deeper than the interpreter's own recursion limit, which is the very thing it exists to
    reject.

    :param query: The caller-supplied query body
    :raises ValidationError: If the query nests deeper than _MAX_QUERY_DEPTH
    """
    stack = [(query, 1)]
    while stack:
        node, depth = stack.pop()
        if depth > _MAX_QUERY_DEPTH:
            raise ValidationError(f'Query is too deeply nested (maximum depth: {_MAX_QUERY_DEPTH}).')
        if isinstance(node, dict):
            stack.extend((value, depth + 1) for value in node.values())
        elif isinstance(node, list):
            stack.extend((item, depth + 1) for item in node)


def _validate_query_input(query) -> None:
    """
    Run the checks that must happen before a query is deserialized through the schema.

    Ordering matters. The depth guard runs first because ``_validate_no_cross_index_keys`` is itself
    recursive and would blow the stack on a pathologically deep query. Both run ahead of field
    deserialization (from a ``pre_load`` hook) so that a cross-index attempt is always reported as
    such, rather than being pre-empted by, or skipped because of, an unrelated field error.

    :param query: The caller-supplied query body
    :raises ValidationError: If the query is too deeply nested or attempts a cross-index lookup
    """
    _validate_query_depth(query)
    _validate_no_cross_index_keys(query)


# Keys permitted inside a nested clause's `inner_hits`. Deliberately excludes `_source`, so a caller
# cannot use inner_hits to select which nested fields come back.
_ALLOWED_INNER_HITS_KEYS = ('from', 'name', 'size')


class BoolQuerySchema(StrictSchema):
    """
    A `bool` query clause.

    Each occupant holds further query clauses, so they recurse back into QueryClauseSchema (via a
    lambda, since that schema is defined below). Inheriting StrictSchema is what rejects any bool
    key the frontend does not send.

    Serialization direction:
    API -> load() -> Python
    """

    must = List(Nested(lambda: QueryClauseSchema()), required=False, allow_none=False)
    must_not = List(Nested(lambda: QueryClauseSchema()), required=False, allow_none=False)
    should = List(Nested(lambda: QueryClauseSchema()), required=False, allow_none=False)
    filter = List(Nested(lambda: QueryClauseSchema()), required=False, allow_none=False)
    # Left untyped, matching the previous hand-rolled validation, which allowlisted the key without
    # constraining its value.
    minimum_should_match = Raw(required=False, allow_none=False)


class NestedQuerySchema(StrictSchema):
    """
    A `nested` query clause.

    `query` recurses back into QueryClauseSchema, which is what keeps a free-form clause from being
    smuggled in below a nested path.

    Serialization direction:
    API -> load() -> Python
    """

    path = String(required=True, allow_none=False)
    query = Nested(lambda: QueryClauseSchema(), required=True, allow_none=False)
    inner_hits = Dict(
        keys=String(
            validate=OneOf(
                _ALLOWED_INNER_HITS_KEYS,
                error="'{input}' is not allowed in inner_hits. Allowed: {choices}.",
            )
        ),
        values=Raw(),
        required=False,
        allow_none=False,
    )
    # Left untyped, matching the previous hand-rolled validation, which allowlisted these keys
    # without constraining their values.
    score_mode = Raw(required=False, allow_none=False)
    ignore_unmapped = Raw(required=False, allow_none=False)


class QueryClauseSchema(StrictSchema):
    """
    A single OpenSearch DSL query clause, restricted to the clause types the CompactConnect frontend
    actually builds (see prepRequestSearchParams in webroot/src/network/searchApi/data.api.ts).

    Because a request is *loaded* through this schema rather than merely inspected, only structure
    described here can reach OpenSearch at all.

    The field-keyed clauses take arbitrary field names, so their contents stay Raw: restricting
    which fields may be *queried* is the job of the permission checks in the search handler, not of
    this schema. Note that `terms` in particular stays permissive so that a terms lookup carrying an
    `index` key is still caught by _validate_no_cross_index_keys with a cross-index error.

    Serialization direction:
    API -> load() -> Python
    """

    match_all = Dict(required=False, allow_none=False)
    term = Dict(keys=String(), values=Raw(), required=False, allow_none=False)
    terms = Dict(
        keys=String(),
        values=List(
            Raw(),
            error_messages={'invalid': 'A terms query must be a plain list of values.'},
        ),
        required=False,
        allow_none=False,
    )
    match = Dict(keys=String(), values=Raw(), required=False, allow_none=False)
    match_phrase_prefix = Dict(keys=String(), values=Raw(), required=False, allow_none=False)
    range = Dict(keys=String(), values=Raw(), required=False, allow_none=False)
    bool = Nested(BoolQuerySchema, required=False, allow_none=False)
    nested = Nested(NestedQuerySchema, required=False, allow_none=False)


# Sort shape the search API accepts, derived from what the CompactConnect frontend actually emits
# (see prepRequestSearchParams in webroot/src/network/searchApi/data.api.ts), which is exactly:
#
#     sort: [{'<field>.keyword': {'order': 'asc' | 'desc'}}]
#
# This is modelled declaratively rather than walked, so anything not described here is rejected by
# marshmallow itself.
_ALLOWED_SORT_ORDERS = ('asc', 'desc')

# Fields a caller is permitted to sort by. The frontend only ever sorts by family name, but
# providerId and the date fields are kept available so `search_after` cursor pagination has a unique
# tiebreaker to sort on.
#
# This list is deliberately restricted to non-sensitive fields. Sort values are echoed back to the
# caller as `lastSort` (see the search handler), which is outside the response schema that strips
# restricted fields -- so whatever is sortable is also readable. Sensitive fields (dateOfBirth,
# emailAddress, phoneNumber, home address, ...) are therefore not sortable by anyone, regardless of
# scopes. Note this is independent of *querying*: querying by dateOfBirth is still supported for
# callers holding readPrivate.
#
# Text fields are only listed via their `.keyword` subfield, since OpenSearch rejects sorting on an
# analyzed text field anyway.
_ALLOWED_SORT_FIELDS = (
    'dateOfExpiration',
    'dateOfUpdate',
    'familyName.keyword',
    'givenName.keyword',
    'providerId',
)


class SortOptionsSchema(StrictSchema):
    """
    Sort options for a single sorted field, e.g. {'order': 'asc'}.

    Inheriting StrictSchema (unknown = RAISE) is what rejects every sort option the frontend does
    not send -- including `nested`, whose `filter` would otherwise be an unvalidated query-DSL
    position.

    Serialization direction:
    API -> load() -> Python
    """

    order = String(
        required=True,
        allow_none=False,
        validate=OneOf(_ALLOWED_SORT_ORDERS, error="Invalid sort order '{input}'. Allowed values: {choices}."),
    )


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

    providerFamGivMid = String(required=False, allow_none=False, validate=Length(2, 400))
    providerDateOfUpdate = Raw(required=False, allow_none=False)
    birthMonthDay = String(required=True, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))

    # Compact Unique Identifier (CUID); only present once a paired single-state/multi-state license exists.
    publicCompactIdentifier = PublicCompactIdentifierField(required=False, allow_none=False)

    # these records are present when getting provider information from the GET endpoint
    # so we check for them here and sanitize them if they are present
    licenses = List(Nested(LicenseReadPrivateResponseSchema(), required=False, allow_none=False))
    privileges = List(Nested(PrivilegeReadPrivateResponseSchema(), required=False, allow_none=False))
    # list of all adverse action records, used by the disciplinary information table
    adverseActions = List(Nested(AdverseActionGeneralResponseSchema(), required=False, allow_none=False))

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

    providerFamGivMid = String(required=False, allow_none=False, validate=Length(2, 400))
    providerDateOfUpdate = Raw(required=False, allow_none=False)
    birthMonthDay = String(required=True, allow_none=False, validate=Regexp('^[0-1]{1}[0-9]{1}-[0-3]{1}[0-9]{1}'))

    # Compact Unique Identifier (CUID); only present once a paired single-state/multi-state license exists.
    publicCompactIdentifier = PublicCompactIdentifierField(required=False, allow_none=False)

    # these records are present when getting provider information from the GET endpoint
    # so we check for them here and sanitize them if they are present
    licenses = List(Nested(LicenseGeneralResponseSchema(), required=False, allow_none=False))
    privileges = List(Nested(PrivilegeGeneralResponseSchema(), required=False, allow_none=False))
    # list of all adverse action records, used by the disciplinary information table
    adverseActions = List(Nested(AdverseActionGeneralResponseSchema(), required=False, allow_none=False))


class ProviderOpenSearchDocumentSchema(ProviderGeneralResponseSchema):
    """
    Provider object fields for OpenSearch document indexing.

    Extends ProviderGeneralResponseSchema with license objects that include dateOfBirth,
    enabling authorized staff users to search providers by date of birth. This schema
    is used only for indexing into OpenSearch, not for API responses.

    Serialization direction:
    Python -> load() -> OpenSearch document
    """

    licenses = List(Nested(LicenseOpenSearchDocumentSchema(), required=False, allow_none=False))


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

    # Compact Unique Identifier (CUID); only present once a paired single-state/multi-state license exists.
    publicCompactIdentifier = PublicCompactIdentifierField(required=False, allow_none=False)

    # Unlike the JCC public provider search, which only returns privilege data for a provider, Social Work returns
    # both licenses and privileges. Adverse actions are also returned (nested under licenses/privileges), but with
    # NPDB category and other staff-only fields stripped via AdverseActionPublicResponseSchema.
    licenses = List(Nested(LicensePublicResponseSchema(), required=False, allow_none=False))
    privileges = List(Nested(PrivilegePublicResponseSchema(), required=False, allow_none=False))


class PublicLicenseSearchResponseSchema(ForgivingSchema):
    """
    License object fields returned by the public query providers endpoint.
    """

    providerId = Raw(required=True, allow_none=False)
    givenName = String(required=True, allow_none=False, validate=Length(1, 100))
    familyName = String(required=True, allow_none=False, validate=Length(1, 100))
    licenseJurisdiction = String(required=True, allow_none=False)
    compact = Compact(required=True, allow_none=False)
    licenseType = String(required=True, allow_none=False)
    licenseScope = LicenseScopeField(required=True, allow_none=False)
    licenseNumber = String(required=True, allow_none=False, validate=Length(1, 100))
    licenseEligibility = CompactEligibility(required=True, allow_none=False)
    # Compact Unique Identifier (CUID); only present once a paired single-state/multi-state license exists.
    publicCompactIdentifier = PublicCompactIdentifierField(required=False, allow_none=False)


class QueryProvidersRequestSchema(CCRequestSchema):
    """
    Schema for staff query providers requests.

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
        licenseNumber = String(required=False, allow_none=False, validate=Length(min=1, max=100))

    class PaginationSchema(ForgivingSchema):
        """
        Nested schema for the pagination object within the request.
        """

        lastKey = String(required=False, allow_none=False, validate=Length(min=1, max=1024))
        pageSize = Integer(required=False, allow_none=False, validate=Range(min=5, max=100))

    class SortingSchema(ForgivingSchema):
        """
        Nested schema for the sorting object within the request.
        """

        key = String(required=False, allow_none=False)
        direction = String(required=False, allow_none=False)

    query = Nested(QuerySchema, required=True, allow_none=False)
    pagination = Nested(PaginationSchema, required=False, allow_none=False)
    sorting = Nested(SortingSchema, required=False, allow_none=False)


class PublicQueryProvidersRequestSchema(CCRequestSchema):
    """
    Request body for the public POST .../providers/query endpoint only.

    The query object allows only jurisdiction, givenName, familyName, and licenseNumber.
    Pagination and sorting match QueryProvidersRequestSchema.
    """

    class PublicQuerySchema(CCRequestSchema):
        """
        Nested schema for the query object within the request.
        """

        jurisdiction = Jurisdiction(required=False, allow_none=False)
        givenName = String(required=False, allow_none=False, validate=Length(min=1, max=100))
        familyName = String(required=False, allow_none=False, validate=Length(min=1, max=100))
        licenseNumber = String(required=False, allow_none=False, validate=Length(min=1, max=100))
        # Anchored, case-insensitive CUID match. This is the primary input guard: it rejects wildcards,
        # partial values, and counter-only lookups before anything is forwarded to OpenSearch. The length cap
        # bounds the cost of regex matching against a maliciously long input; a real CUID is never anywhere
        # close to this long, since the counter would have to reach an implausible number of digits.
        cuid = String(
            required=False,
            allow_none=False,
            validate=[Length(max=64), Regexp(CUID_PATTERN, flags=re.IGNORECASE)],
        )
        # Validated for shape here; validated against config.license_types_for_compact(compact) in the handler,
        # since the compact is a path parameter and not available to this schema.
        licenseType = String(required=False, allow_none=False, validate=Length(min=1, max=100))

    query = Nested(PublicQuerySchema, required=True, allow_none=False)
    pagination = Nested(QueryProvidersRequestSchema.PaginationSchema, required=False, allow_none=False)
    sorting = Nested(QueryProvidersRequestSchema.SortingSchema, required=False, allow_none=False)


class SearchProvidersRequestSchema(CCRequestSchema):
    """
    Schema for advanced search providers requests.

    This schema is used to validate incoming requests to the advanced search providers API endpoint.
    It accepts an OpenSearch DSL query body, restricted to the clause types QueryClauseSchema
    declares -- the ones the frontend actually builds. Free-form and scripted clauses are not
    accepted; see QueryClauseSchema for why.

    The request body closely mirrors OpenSearch DSL for pagination using `search_after`.
    See: https://docs.opensearch.org/latest/search-plugins/searching-data/paginate/#the-search_after-parameter

    Serialization direction:
    API -> load() -> Python
    """

    # The OpenSearch query body, restricted to the clause types QueryClauseSchema declares
    query = Nested(QueryClauseSchema, required=True, allow_none=False)

    # Pagination parameters following OpenSearch DSL
    # 'from' is a reserved word in Python, so we use 'from_' with data_key='from'
    from_ = Integer(required=False, allow_none=False, data_key='from', validate=Range(min=0, max=9900))
    size = Integer(required=False, allow_none=False, validate=Range(min=1, max=100))

    # Sort order - required when using search_after pagination
    # Example: [{"providerId": "asc"}, {"dateOfUpdate": "desc"}]
    sort = List(
        Dict(
            keys=String(
                validate=OneOf(
                    _ALLOWED_SORT_FIELDS,
                    error="Sorting by '{input}' is not allowed. Sortable fields: {choices}.",
                )
            ),
            values=Nested(SortOptionsSchema),
        ),
        required=False,
        allow_none=False,
    )

    # The search_after parameter for cursor-based pagination
    # This should be the 'sort' values from the last hit of the previous page
    # Example: ["provider-uuid-123", "2024-01-15T10:30:00Z"]
    search_after = Raw(required=False, allow_none=False)

    @pre_load
    def validate_search_request_dsl(self, data, **kwargs):
        """
        Validate the caller-supplied OpenSearch DSL in the search request body.

        Three application-layer checks are applied:

        1. Query clause allowlist: only the structured query types the frontend builds are accepted.
           Free-form and scripted clauses are rejected, since they can carry a field reference
           inside a string value and thereby slip past field-level permission checks.
        2. Cross-index lookups: queries that attempt to reach another compact's index are blocked.
           Note that this application-layer check is currently the only protection against
           cross-index lookups. The OpenSearch domain setting
           `rest.action.multi.allow_explicit_index: false` would provide a second layer, but it is
           not configured on the domain (see stacks/search_persistent_stack/provider_search_domain.py).

           Dangerous patterns blocked:
           - Terms lookup with external index: {"terms": {"field": {"index": "other_index", ...}}}
           - More like this with external docs: {"more_like_this": {"like": [{"_index": "other"}]}}
        """
        # Runs ahead of field deserialization, so `data` is still exactly what the caller sent and
        # is not guaranteed to be an object. Anything else is left for the field layer to reject.
        if isinstance(data, dict):
            _validate_query_input(data.get('query', {}))
        return data
