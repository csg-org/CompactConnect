from cc_common.data_model.schema.common import CCEnum


class MilitaryAffiliationStatus(CCEnum):
    INITIALIZING = 'initializing'
    ACTIVE = 'active'
    INACTIVE = 'inactive'


class MilitaryAffiliationType(CCEnum):
    MILITARY_MEMBER = 'militaryMember'
    MILITARY_MEMBER_SPOUSE = 'militaryMemberSpouse'


SUPPORTED_MILITARY_AFFILIATION_FILE_EXTENSIONS = ('pdf', 'jpg', 'jpeg', 'png', 'docx')
MILITARY_AFFILIATIONS_DOCUMENT_TYPE_KEY_NAME = 'military-affiliations'

MILITARY_AFFILIATION_RECORD_TYPE = 'militaryAffiliation'
