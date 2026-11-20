import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import invoice_report  # noqa: E402 module path is the lambda root, not a package


class TestInvoiceReport(unittest.TestCase):
    def test_first_upload_in_the_billing_month_is_new_and_keeps_both_dates(self):
        item = invoice_report.line_item(
            {
                'jurisdictionUploadedCompactEligibility': 'eligible',
                'licenseType': 'esthetician',
                'licenseNumber': 'COS-1',
                'givenName': 'Jane',
                'familyName': 'Smith',
                'jurisdiction': 'oh',
                'firstUploadDate': '2024-09-10T00:00:00Z',
                'dateOfIssuance': '2024-09-05',
                'dateOfRenewal': '2024-09-15',
            },
            'oh',
            '2024-09',
            renewal_uploaded=True,
            fee=25,
        )

        self.assertEqual('new', item['category'])
        self.assertEqual('2024-09-10', item['uploadDate'])
        self.assertEqual('2024-09-05', item['issuanceDate'])
        self.assertIsNone(item['renewalDate'])

    def test_renewal_upload_is_billed_when_the_renewal_date_is_earlier(self):
        item = invoice_report.line_item(
            {
                'jurisdictionUploadedCompactEligibility': 'eligible',
                'licenseType': 'cosmetologist',
                'licenseNumber': 'COS-2',
                'firstUploadDate': '2022-01-10T00:00:00Z',
                'dateOfIssuance': '2022-01-01',
                'dateOfRenewal': '2024-07-15',
            },
            'oh',
            '2024-09',
            renewal_uploaded=True,
            fee=25,
        )

        self.assertEqual('renewal', item['category'])
        self.assertEqual('2022-01-10', item['uploadDate'])
        self.assertEqual('2022-01-01', item['issuanceDate'])
        self.assertEqual('2024-07-15', item['renewalDate'])

    def test_renewal_without_a_renewal_date_is_still_billed(self):
        item = invoice_report.line_item(
            {
                'jurisdictionUploadedCompactEligibility': 'eligible',
                'licenseType': 'cosmetologist',
                'licenseNumber': 'COS-3',
                'firstUploadDate': '2022-01-10T00:00:00Z',
                'dateOfIssuance': '2022-01-01',
            },
            'oh',
            '2024-09',
            renewal_uploaded=True,
            fee=25,
        )

        self.assertEqual('renewal', item['category'])
        self.assertIsNone(item['renewalDate'])

    def test_a_renewal_date_in_the_month_is_not_enough_without_a_renewal_upload(self):
        item = invoice_report.line_item(
            {
                'jurisdictionUploadedCompactEligibility': 'eligible',
                'licenseType': 'cosmetologist',
                'licenseNumber': 'COS-4',
                'firstUploadDate': '2022-01-10T00:00:00Z',
                'dateOfRenewal': '2024-09-15',
            },
            'oh',
            '2024-09',
            renewal_uploaded=False,
            fee=25,
        )

        self.assertIsNone(item)

    def test_ineligible_license_is_not_billed(self):
        item = invoice_report.line_item(
            {
                'jurisdictionUploadedCompactEligibility': 'ineligible',
                'licenseType': 'esthetician',
                'licenseNumber': 'COS-5',
                'firstUploadDate': '2024-09-10T00:00:00Z',
            },
            'oh',
            '2024-09',
            renewal_uploaded=False,
            fee=25,
        )

        self.assertIsNone(item)

    def test_duplicate_index_hits_collapse_and_a_renewal_hit_wins(self):
        indexed = invoice_report.indexed_licenses(
            'cosm',
            'oh',
            [
                {
                    'providerId': 'provider-1',
                    'licenseUploadDateGSISK': 'TIME#1#LT#esth#PID#provider-1',
                    'updateType': 'other',
                },
                {
                    'licenseUploadDateGSISK': 'TIME#2#LT#esth#PID#provider-1',
                    'updateType': 'renewal',
                },
            ],
        )

        self.assertEqual(1, len(indexed))
        self.assertTrue(indexed[0]['renewalUploaded'])
        self.assertEqual('cosm#PROVIDER#license/oh/esth#', indexed[0]['key']['sk'])

    def test_zip_contains_one_csv_per_state_for_that_license_type(self):
        alabama = invoice_report.state_invoice_csv(
            'Alabama',
            [
                {
                    'givenName': 'Ann',
                    'familyName': 'Lee',
                    'homeState': 'AL',
                    'licenseNumber': 'A-1',
                    'category': 'new',
                    'uploadDate': '2026-09-02',
                    'issuanceDate': '2026-09-01',
                    'renewalDate': None,
                    'fee': 25,
                }
            ],
        )
        ohio = invoice_report.state_invoice_csv('Ohio', [])
        generated_at = '2026-11-20T151130Z'
        alabama_name = invoice_report.invoice_filename('esthetician', '2026-09', 'Alabama', 'al', generated_at)
        ohio_name = invoice_report.invoice_filename('esthetician', '2026-09', 'Ohio', 'oh', generated_at)
        payload = invoice_report.invoice_zip([(alabama_name, alabama), (ohio_name, ohio)])
        entries = invoice_report.read_zip_entries(payload)

        self.assertEqual([alabama_name, ohio_name], list(entries))
        self.assertEqual('alabama-esthetician-invoice-2026-09-run-2026-11-20T151130Z.csv', alabama_name)
        alabama_csv = entries[alabama_name]
        self.assertIn('Ann,Lee,AL,A-1,New,2026-09-02,2026-09-01,,$25.00', alabama_csv)
        self.assertIn('Total Billable,0', entries[ohio_name])
        self.assertNotIn('Total Uploaded', alabama)
        self.assertEqual(
            'compact/cosm/reports/invoices/license-type/esthetician/2026/09/'
            'esthetician-2026-09-invoice-run-2026-11-20T151130Z.zip',
            invoice_report.invoice_object_key('cosm', 'esthetician', '2026-09', generated_at),
        )


if __name__ == '__main__':
    unittest.main()
