//
//  PrivilegePurchaseOption.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//
import {
    PrivilegePurchaseOption,
    PrivilegePurchaseOptionSerializer
} from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { State } from '@models/State/State.model';
import i18n from '@/i18n';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('PrivilegePurchaseOption model', () => {
    before(() => {
        const { tm: $tm } = i18n.global;

        (window as any).Vue = {
            config: {
                globalProperties: {
                    $tm,
                }
            }
        };
        i18n.global.locale = 'en';
    });
    it('should create a PrivilegePurchaseOption with expected defaults', () => {
        const privilegePurchaseOption = new PrivilegePurchaseOption();

        // Test field values
        expect(privilegePurchaseOption).to.be.an.instanceof(PrivilegePurchaseOption);
        expect(privilegePurchaseOption.jurisdiction).to.be.an.instanceof(State);
        expect(privilegePurchaseOption.jurisdiction.id).to.equal(null);
        expect(privilegePurchaseOption.jurisdiction.abbrev).to.equal('');
        expect(privilegePurchaseOption.compactType).to.equal(null);
        expect(privilegePurchaseOption.fees).to.matchPattern({});
        expect(privilegePurchaseOption.isJurisprudenceRequired).to.equal(false);
        expect(privilegePurchaseOption.jurisprudenceInfoUri).to.equal('');
    });
    it('should create a PrivilegePurchaseOption with specific values', () => {
        const data = {
            jurisdiction: new State({ abbrev: 'ca' }),
            compactType: 'aslp',
            fees: {
                aud: {
                    baseRate: 100,
                    militaryRate: 50
                },
                slp: {
                    baseRate: 100,
                }
            },
            isJurisprudenceRequired: true,
            jurisprudenceInfoUri: 'https://example.com',
        };
        const privilegePurchaseOption = new PrivilegePurchaseOption(data);

        expect(privilegePurchaseOption).to.be.an.instanceof(PrivilegePurchaseOption);
        expect(privilegePurchaseOption.jurisdiction).to.be.an.instanceof(State);
        expect(privilegePurchaseOption.jurisdiction.abbrev).to.equal('ca');
        expect(privilegePurchaseOption.compactType).to.equal(data.compactType);
        expect(privilegePurchaseOption.fees).to.matchPattern({
            aud: {
                baseRate: 100,
                militaryRate: 50
            },
            slp: {
                baseRate: 100,
            }
        });
        expect(privilegePurchaseOption.isJurisprudenceRequired).to.equal(true);
        expect(privilegePurchaseOption.jurisprudenceInfoUri).to.equal(data.jurisprudenceInfoUri);
    });
    it('should create a PrivilegePurchaseOption with specific values through serializer', () => {
        const data = {
            jurisdictionName: 'kentucky',
            postalAbbreviation: 'ky',
            compact: 'aslp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'aud',
                    amount: 200,
                    militaryRate: 150
                },
                {
                    licenseTypeAbbreviation: 'slp',
                    amount: 100
                }
            ],
            jurisprudenceRequirements: {
                required: true,
                linkToDocumentation: 'https://example.com',
            },
            type: 'jurisdiction'
        };

        const privilegePurchaseOption = PrivilegePurchaseOptionSerializer.fromServer(data);

        // Test field values
        expect(privilegePurchaseOption).to.be.an.instanceof(PrivilegePurchaseOption);
        expect(privilegePurchaseOption.jurisdiction).to.be.an.instanceof(State);
        expect(privilegePurchaseOption.jurisdiction.abbrev).to.equal('ky');
        expect(privilegePurchaseOption.compactType).to.equal('aslp');
        expect(privilegePurchaseOption.fees).to.matchPattern({
            aud: {
                baseRate: 200,
                militaryRate: 150
            },
            slp: {
                baseRate: 100,
            }
        });
        expect(privilegePurchaseOption.isJurisprudenceRequired).to.equal(true);
        expect(privilegePurchaseOption.jurisprudenceInfoUri).to.equal('https://example.com');
    });
    it('should create a PrivilegePurchaseOption with specific values and not throw errors for malformed fee object', () => {
        const data = {
            jurisdictionName: 'kentucky',
            postalAbbreviation: 'ky',
            compact: 'aslp',
            privilegeFees: [
                {
                    licenseTypeAbbreviation: 'aud'
                }
            ],
            jurisprudenceRequirements: {
                required: true,
                linkToDocumentation: 'https://example.com',
            },
            type: 'jurisdiction'
        };

        const privilegePurchaseOption = PrivilegePurchaseOptionSerializer.fromServer(data);

        // Test field values
        expect(privilegePurchaseOption).to.be.an.instanceof(PrivilegePurchaseOption);
        expect(privilegePurchaseOption.jurisdiction).to.be.an.instanceof(State);
        expect(privilegePurchaseOption.jurisdiction.abbrev).to.equal('ky');
        expect(privilegePurchaseOption.compactType).to.equal('aslp');
        expect(privilegePurchaseOption.fees).to.matchPattern({
            aud: {
                baseRate: 0
            }
        });
        expect(privilegePurchaseOption.isJurisprudenceRequired).to.equal(true);
        expect(privilegePurchaseOption.jurisprudenceInfoUri).to.equal('https://example.com');
    });
});
