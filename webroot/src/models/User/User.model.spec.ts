//
//  User.model.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/2020.
//
import { compacts as compactConfigs } from '@/app.config';
import { User, StaffUserSerializer, LicenseeUserSerializer } from '@models/User/User.model';
import { LicenseeSerializer } from '@models/Licensee/Licensee.model';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import i18n from '@/i18n';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('User model', () => {
    before(() => {
        const { tm: $tm, t: $t } = i18n.global;

        (window as any).Vue = {
            config: {
                globalProperties: {
                    $tm,
                    $t,
                }
            }
        };
    });
    it('should create a User with expected defaults', () => {
        const user = new User();

        expect(user).to.be.an.instanceof(User);
        expect(user.id).to.equal(null);
        expect(user.email).to.equal(null);
        expect(user.firstName).to.equal(null);
        expect(user.lastName).to.equal(null);
        expect(user.permissions).to.matchPattern([]);
        expect(user.accountStatus).to.equal('');
        expect(user.getFullName()).to.equal('');
        expect(user.getInitials()).to.equal('');
        expect(user.permissionsShortDisplay()).to.equal('');
        expect(user.permissionsShortDisplay(CompactType.ASLP)).to.equal('');
        expect(user.permissionsFullDisplay()).to.matchPattern([]);
        expect(user.permissionsFullDisplay(CompactType.ASLP)).to.matchPattern([]);
        expect(user.getStateListDisplay([])).to.equal('');
        expect(user.getStateListDisplay(['1', '2', '3'])).to.equal('1, 2 +');
        expect(user.affiliationDisplay()).to.equal('');
        expect(user.affiliationDisplay(CompactType.ASLP)).to.equal('');
        expect(user.statesDisplay()).to.equal('');
        expect(user.statesDisplay(CompactType.ASLP)).to.equal('');
        expect(user.accountStatusDisplay()).to.equal('');
    });
    it('should create a User with specific values (compact-level permission)', () => {
        const data = {
            id: 'id',
            email: 'email',
            firstName: 'firstName',
            lastName: 'lastName',
            permissions: [
                {
                    compact: new Compact({ type: CompactType.ASLP }),
                    isRead: true,
                    isAdmin: true,
                    states: [
                        {
                            state: new State({ abbrev: 'co' }),
                            isWrite: true,
                            isAdmin: true,
                        },
                    ],
                },
            ],
            accountStatus: 'active',
        };
        const user = new User(data);

        expect(user).to.be.an.instanceof(User);
        expect(user.id).to.equal(data.id);
        expect(user.email).to.equal(data.email);
        expect(user.firstName).to.equal(data.firstName);
        expect(user.lastName).to.equal(data.lastName);
        expect(user.permissions).to.matchPattern([
            {
                compact: new Compact({ type: CompactType.ASLP }),
                isRead: true,
                isAdmin: true,
                states: [
                    {
                        isWrite: true,
                        isAdmin: true,
                        '...': '',
                    },
                ],
            },
        ]);
        expect(user.accountStatus).to.equal(data.accountStatus);
        expect(user.getFullName()).to.equal(`${data.firstName} ${data.lastName}`);
        expect(user.getInitials()).to.equal('FL');
        expect(user.permissionsShortDisplay()).to.equal('Read, Admin');
        expect(user.permissionsFullDisplay()).to.matchPattern([
            'ASLP: Read, Admin',
            'Colorado: Write, Admin',
        ]);
        expect(user.affiliationDisplay()).to.equal('ASLP');
        expect(user.statesDisplay()).to.equal('Colorado');
        expect(user.accountStatusDisplay()).to.equal('Active');
    });
    it('should create a User with specific values (compact-level permission)', () => {
        const data = {
            permissions: [
                {
                    compact: new Compact({ type: CompactType.ASLP }),
                    isRead: false,
                    isAdmin: true,
                    states: [
                        {
                            state: new State({ abbrev: 'co' }),
                            isWrite: true,
                            isAdmin: true,
                        },
                    ],
                },
            ],
        };
        const user = new User(data);

        expect(user).to.be.an.instanceof(User);
        expect(user.permissionsShortDisplay()).to.equal('Admin');
        expect(user.permissionsFullDisplay()).to.matchPattern([
            'ASLP: Admin',
            'Colorado: Write, Admin',
        ]);
        expect(user.affiliationDisplay()).to.equal('ASLP');
        expect(user.statesDisplay()).to.equal('Colorado');
    });
    it('should create a User with specific values (state-level permission)', () => {
        const data = {
            permissions: [
                {
                    compact: new Compact({ type: CompactType.ASLP }),
                    isRead: false,
                    isAdmin: false,
                    states: [
                        {
                            state: new State({ abbrev: 'co' }),
                            isWrite: true,
                            isAdmin: true,
                        },
                    ],
                },
            ],
        };
        const user = new User(data);

        expect(user).to.be.an.instanceof(User);
        expect(user.permissionsShortDisplay(CompactType.ASLP)).to.equal('Write, Admin');
        expect(user.permissionsFullDisplay()).to.matchPattern([
            'Colorado: Write, Admin',
        ]);
        expect(user.affiliationDisplay(CompactType.ASLP)).to.equal('Colorado');
        expect(user.statesDisplay(CompactType.ASLP)).to.equal('Colorado');
    });
    it('should create a User with specific values (state-level permission)', () => {
        const data = {
            permissions: [
                {
                    compact: new Compact({ type: CompactType.ASLP }),
                    isRead: false,
                    isAdmin: false,
                    states: [
                        {
                            state: new State({ abbrev: 'xx' }),
                            isWrite: false,
                            isAdmin: true,
                        },
                        {
                            state: new State({ abbrev: 'co' }),
                            isWrite: false,
                            isAdmin: true,
                        },
                        {
                            state: new State({ abbrev: 'md' }),
                            isWrite: false,
                            isAdmin: true,
                        },
                    ],
                },
            ],
        };
        const user = new User(data);

        expect(user).to.be.an.instanceof(User);
        expect(user.permissionsShortDisplay(CompactType.ASLP)).to.equal('Admin');
        expect(user.permissionsFullDisplay()).to.matchPattern([
            'Unknown: Admin',
            'Colorado: Admin',
            'Maryland: Admin',
        ]);
        expect(user.affiliationDisplay(CompactType.ASLP)).to.equal('Unknown, Colorado +');
        expect(user.statesDisplay(CompactType.ASLP)).to.equal('Unknown, Colorado +');
    });
    it('should create a staff user with specific values through staff serializer', () => {
        const data = {
            userId: 'id',
            status: 'active',
            attributes: {
                email: 'email',
                givenName: 'firstName',
                familyName: 'lastName',
            },
            permissions: {
                aslp: {
                    actions: {
                        read: true,
                        admin: true,
                    },
                    jurisdictions: {
                        co: {
                            actions: {
                                write: true,
                                admin: true,
                            },
                        },
                    },
                },
            },
        };
        const user = StaffUserSerializer.fromServer(data, { pageNum: 1 });

        expect(user).to.be.an.instanceof(User);
        expect(user.id).to.equal(data.userId);
        expect(user.email).to.equal(data.attributes.email);
        expect(user.firstName).to.equal(data.attributes.givenName);
        expect(user.lastName).to.equal(data.attributes.familyName);
        expect(user.permissions).to.matchPattern([
            {
                compact: {
                    type: CompactType.ASLP,
                    memberStates: compactConfigs.aslp.memberStates.map((memberState) => ({
                        abbrev: memberState,
                        '...': '',
                    })),
                    '...': '',
                },
                isRead: true,
                isAdmin: true,
                states: [
                    {
                        isWrite: true,
                        isAdmin: true,
                        '...': '',
                    },
                ],
            },
        ]);
        expect(user.accountStatus).to.equal(data.status);
        expect(user.serverPage).to.equal(1);
        expect(user.getFullName()).to.equal(`${data.attributes.givenName} ${data.attributes.familyName}`);
        expect(user.getInitials()).to.equal('FL');
        expect(user.permissionsShortDisplay()).to.equal('Read, Admin');
        expect(user.permissionsFullDisplay()).to.matchPattern([
            'ASLP: Read, Admin',
            'Colorado: Write, Admin',
        ]);
        expect(user.affiliationDisplay()).to.equal('ASLP');
        expect(user.statesDisplay()).to.equal('Colorado');
        expect(user.accountStatusDisplay()).to.equal('Active');
    });
    it('should create a licensee user with specific values through licensee serializer', () => {
        const data = {
            privileges: [
                {
                    licenseJurisdiction: 'al',
                    dateOfExpiration: '2024-08-29',
                    compact: 'aslp',
                    providerId: '2',
                    type: 'privilege',
                    dateOfIssuance: '2024-08-29',
                    dateOfUpdate: '2024-08-29',
                    status: 'active'
                }
            ],
            licenseJurisdiction: 'co',
            compact: 'aslp',
            homeAddressStreet2: '',
            npi: '2522457223',
            homeAddressPostalCode: '80302',
            givenName: 'Tyler',
            homeAddressStreet1: '1045 Pearl St',
            militaryWaiver: true,
            dateOfBirth: '1975-01-01',
            privilegeJurisdictions: [
                'al'
            ],
            type: 'provider',
            ssn: '748-19-5032',
            licenseType: 'audiologist',
            licenses: [
                {
                    compact: 'aslp',
                    homeAddressStreet2: '',
                    npi: '2522457223',
                    homeAddressPostalCode: '80302',
                    jurisdiction: 'co',
                    givenName: 'Tyler',
                    homeAddressStreet1: '1045 Pearl St',
                    militaryWaiver: true,
                    dateOfBirth: '1975-01-01',
                    type: 'license-home',
                    dateOfIssuance: '2024-08-29',
                    ssn: '748-19-5032',
                    licenseType: 'audiologist',
                    dateOfExpiration: '2024-08-29',
                    homeAddressState: 'co',
                    providerId: '2',
                    dateOfRenewal: '2024-08-29',
                    familyName: 'Durden',
                    homeAddressCity: 'Boulder',
                    middleName: '',
                    dateOfUpdate: '2024-08-29',
                    status: 'inactive'
                }
            ],
            emailAddress: 'asfadfd@slsgfss.com',
            dateOfExpiration: '2024-08-29',
            homeAddressState: 'co',
            providerId: '2',
            familyName: 'Durden',
            homeAddressCity: 'Boulder',
            middleName: '',
            birthMonthDay: '1975-01-01',
            dateOfUpdate: '2024-08-29',
            status: 'inactive'
        };
        const user = LicenseeUserSerializer.fromServer(data);
        const licensee = LicenseeSerializer.fromServer(data);

        expect(user).to.be.an.instanceof(User);
        expect(user.id).to.equal(data.providerId);
        expect(user.email).to.equal(data.emailAddress);
        expect(user.firstName).to.equal(data.givenName);
        expect(user.lastName).to.equal(data.familyName);
        expect(typeof user.licensee).to.equal(typeof licensee);
        expect(user.accountStatus).to.equal(data.status);
        expect(user.getFullName()).to.equal(`${data.givenName} ${data.familyName}`);
        expect(user.getInitials()).to.equal('TD');
        expect(user.accountStatusDisplay()).to.equal('Inactive');
    });
});
