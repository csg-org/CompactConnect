import json
import os


class SandboxBootstrapConfig:
    """Configuration class for sandbox bootstrap script."""

    def __init__(self, config_file_path: str | None = None):
        """Initialize configuration from JSON file.

        :param config_file_path: Path to configuration JSON file. If None, uses default location.
        """
        if config_file_path is None:
            config_file_path = os.path.join(os.path.dirname(__file__), 'sandbox_bootstrap_config.json')

        with open(config_file_path) as f:
            self._config = json.load(f)

    @property
    def base_email(self) -> str:
        """Get the base email address for creating test users."""
        return self._config['base_email']

    @property
    def email_parts(self) -> tuple[str, str]:
        """Get the email username and domain parts."""
        if '@' not in self.base_email or self.base_email.count('@') > 1:
            raise ValueError(f'Invalid email format: {self.base_email}')

        username, domain = self.base_email.split('@')
        return username, domain

    @property
    def authorize_net_api_login_id(self) -> str:
        """Get the authorize.net API login ID."""
        return self._config['authorize_net']['api_login_id']

    @property
    def authorize_net_transaction_key(self) -> str:
        """Get the authorize.net transaction key."""
        return self._config['authorize_net']['transaction_key']

    @property
    def compact_abbreviation(self) -> str:
        """Get the compact abbreviation."""
        return self._config['compact']['abbreviation']

    @property
    def additional_states(self) -> list[str]:
        """Get the list of additional states to configure."""
        return self._config['compact']['additional_states']

    @property
    def commission_fee(self) -> dict:
        """Get the commission fee configuration."""
        return self._config['compact']['commission_fee']

    @property
    def transaction_fee(self) -> dict:
        """Get the transaction fee configuration."""
        return self._config['compact']['transaction_fee']

    @property
    def privilege_fees(self) -> dict:
        """Get the privilege fees configuration."""
        return self._config['compact']['privilege_fees']

    @property
    def test_provider(self) -> dict:
        """Get the test provider data."""
        return self._config['test_data']['provider']

    @property
    def test_license(self) -> dict:
        """Get the test license data."""
        return self._config['test_data']['license']

    @property
    def jurisprudence_requirements(self) -> dict:
        """Get the jurisprudence requirements configuration."""
        return self._config['jurisdiction']['jurisprudence_requirements']

    def get_compact_config(self) -> dict:
        """Get the complete compact configuration for API calls."""
        return {
            'compactCommissionFee': {
                'feeAmount': self.commission_fee['amount'],
                'feeType': self.commission_fee['type'],
            },
            'licenseeRegistrationEnabled': True,
            'compactOperationsTeamEmails': [self.base_email],
            'compactAdverseActionsNotificationEmails': [self.base_email],
            'compactSummaryReportNotificationEmails': [self.base_email],
            'transactionFeeConfiguration': {
                'licenseeCharges': {
                    'chargeAmount': self.transaction_fee['amount'],
                    'chargeType': self.transaction_fee['type'],
                    'active': self.transaction_fee['active'],
                }
            },
            'configuredStates': [{'postalAbbreviation': state, 'isLive': True} for state in self.additional_states],
        }

    def get_jurisdiction_config(self, privilege_fees: list) -> dict:
        """Get the jurisdiction configuration for API calls.

        :param privilege_fees: List of privilege fee configurations
        :return: Jurisdiction configuration dictionary
        """
        return {
            'jurisdictionOperationsTeamEmails': [self.base_email],
            'jurisdictionAdverseActionsNotificationEmails': [self.base_email],
            'jurisdictionSummaryReportNotificationEmails': [self.base_email],
            'licenseeRegistrationEnabled': True,
            'jurisprudenceRequirements': self.jurisprudence_requirements,
            'privilegeFees': privilege_fees,
        }

    def get_license_data(self) -> dict:
        """Get the license data for API calls."""
        return {
            'npi': self.test_license['npi'],
            'licenseNumber': self.test_license['license_number'],
            'homeAddressPostalCode': self.test_license['home_address_postal_code'],
            'givenName': self.test_provider['given_name'],
            'familyName': self.test_provider['family_name'],
            'homeAddressStreet1': self.test_license['home_address_street1'],
            'dateOfBirth': self.test_license['date_of_birth'],
            'dateOfIssuance': self.test_license['date_of_issuance'],
            'ssn': self.test_provider['ssn'],
            'licenseType': self.test_license['license_type'],
            'dateOfExpiration': self.test_license['date_of_expiration'],
            'homeAddressState': self.test_license['home_address_state'],
            'dateOfRenewal': self.test_license['date_of_renewal'],
            'homeAddressCity': self.test_license['home_address_city'],
            'compactEligibility': self.test_license['compact_eligibility'],
            'licenseStatus': self.test_license['license_status'],
        }
