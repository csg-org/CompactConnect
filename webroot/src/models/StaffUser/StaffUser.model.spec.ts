//
//  User.model.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/2020.
//
import { AuthTypes, Permission } from '@/app.config';
import { StaffUser, StaffUserSerializer } from '@models/StaffUser/StaffUser.model';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import i18n from '@/i18n';

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('Staff User model', () => {
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
    it('should create a Staff User with expected defaults', () => {
        const user = new StaffUser();

        expect(user).to.be.an.instanceof(StaffUser);
        expect(user.id).to.equal(null);
        expect(user.compactConnectEmail).to.equal(null);
        expect(user.firstName).to.equal(null);
        expect(user.lastName).to.equal(null);
        expect(user.userType).to.equal(null);
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
        expect(user.hasPermission(Permission.READ_PRIVATE, CompactType.ASLP)).to.equal(false);
        expect(user.accountStatusDisplay()).to.equal('');
    });
    it('should create a Staff User with specific values (compact-level permission)', () => {
        const data = {
            id: 'id',
            email: 'email',
            firstName: 'firstName',
            lastName: 'lastName',
            permissions: [
                {
                    compact: new Compact({ type: CompactType.ASLP }),
                    isReadPrivate: true,
                    isReadSsn: true,
                    isAdmin: true,
                    states: [
                        {
                            state: new State({ abbrev: 'co' }),
                            isReadPrivate: true,
                            isReadSsn: true,
                            isWrite: true,
                            isAdmin: true,
                        },
                    ],
                },
            ],
            userType: AuthTypes.STAFF,
            accountStatus: 'active',
        };
        const user = new StaffUser(data);

        expect(user).to.be.an.instanceof(StaffUser);
        expect(user.id).to.equal(data.id);
        expect(user.email).to.equal(data.email);
        expect(user.userType).to.equal(data.userType);
        expect(user.firstName).to.equal(data.firstName);
        expect(user.lastName).to.equal(data.lastName);
        expect(user.permissions).to.matchPattern([
            {
                compact: new Compact({ type: CompactType.ASLP }),
                isReadPrivate: true,
                isReadSsn: true,
                isAdmin: true,
                states: [
                    {
                        isReadPrivate: true,
                        isReadSsn: true,
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
        expect(user.permissionsShortDisplay()).to.equal('Read Private, Read SSN, Admin');
        expect(user.permissionsFullDisplay()).to.matchPattern([
            'ASLP: Read Private, Read SSN, Admin',
            'Colorado: Read Private, Read SSN, Write, Admin',
        ]);
        expect(user.affiliationDisplay()).to.equal('ASLP');
        expect(user.statesDisplay()).to.equal('Colorado');
        expect(user.hasPermission(Permission.READ_PRIVATE, CompactType.ASLP)).to.equal(true);
        expect(user.accountStatusDisplay()).to.equal('Active');
    });
    it('should create a Staff User with specific values (compact-level permission)', () => {
        const data = {
            permissions: [
                {
                    compact: new Compact({ type: CompactType.ASLP }),
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
        const user = new StaffUser(data);

        expect(user).to.be.an.instanceof(StaffUser);
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
                    states: [
                        {
                            state: new State({ abbrev: 'co' }),
                            isReadPrivate: true,
                            isWrite: true,
                            isAdmin: true,
                        },
                    ],
                },
            ],
        };
        const user = new StaffUser(data);

        expect(user).to.be.an.instanceof(StaffUser);
        expect(user.permissionsShortDisplay(CompactType.ASLP)).to.equal('Read Private, Write, Admin');
        expect(user.permissionsFullDisplay()).to.matchPattern([
            'Colorado: Read Private, Write, Admin',
        ]);
        expect(user.affiliationDisplay(CompactType.ASLP)).to.equal('Colorado');
        expect(user.statesDisplay(CompactType.ASLP)).to.equal('Colorado');
    });
    it('should create a Staff User with specific values (state-level permission)', () => {
        const data = {
            permissions: [
                {
                    compact: new Compact({ type: CompactType.ASLP }),
                    states: [
                        {
                            state: new State({ abbrev: 'xx' }),
                            isAdmin: true,
                        },
                        {
                            state: new State({ abbrev: 'co' }),
                            isAdmin: true,
                        },
                        {
                            state: new State({ abbrev: 'md' }),
                            isAdmin: true,
                        },
                    ],
                },
            ],
        };
        const user = new StaffUser(data);

        expect(user).to.be.an.instanceof(StaffUser);
        expect(user.permissionsShortDisplay(CompactType.ASLP)).to.equal('Admin');
        expect(user.permissionsFullDisplay()).to.matchPattern([
            'Unknown: Admin',
            'Colorado: Admin',
            'Maryland: Admin',
        ]);
        expect(user.affiliationDisplay(CompactType.ASLP)).to.equal('Unknown, Colorado +');
        expect(user.statesDisplay(CompactType.ASLP)).to.equal('Unknown, Colorado +');
    });
    it('should create a Staff User with specific values through staff serializer', () => {
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
                        readPrivate: true,
                        readSSN: true,
                        admin: true,
                    },
                    jurisdictions: {
                        co: {
                            actions: {
                                readPrivate: true,
                                readSSN: true,
                                write: true,
                                admin: true,
                            },
                        },
                    },
                },
            },
        };
        const user = StaffUserSerializer.fromServer(data, { pageNum: 1 });

        expect(user).to.be.an.instanceof(StaffUser);
        expect(user.id).to.equal(data.userId);
        expect(user.compactConnectEmail).to.equal(data.attributes.email);
        expect(user.firstName).to.equal(data.attributes.givenName);
        expect(user.lastName).to.equal(data.attributes.familyName);
        expect(user.permissions).to.matchPattern([
            {
                compact: {
                    type: CompactType.ASLP,
                    '...': '',
                },
                isReadPrivate: true,
                isReadSsn: true,
                isAdmin: true,
                states: [
                    {
                        isReadPrivate: true,
                        isReadSsn: true,
                        isWrite: true,
                        isAdmin: true,
                        '...': '',
                    },
                ],
            },
        ]);
        expect(user.accountStatus).to.equal(data.status);
        expect(user.serverPage).to.equal(1);
        expect(user.userType).to.equal(AuthTypes.STAFF);
        expect(user.getFullName()).to.equal(`${data.attributes.givenName} ${data.attributes.familyName}`);
        expect(user.getInitials()).to.equal('FL');
        expect(user.permissionsShortDisplay()).to.equal('Read Private, Read SSN, Admin');
        expect(user.permissionsFullDisplay()).to.matchPattern([
            'ASLP: Read Private, Read SSN, Admin',
            'Colorado: Read Private, Read SSN, Write, Admin',
        ]);
        expect(user.affiliationDisplay()).to.equal('ASLP');
        expect(user.statesDisplay()).to.equal('Colorado');
        expect(user.hasPermission(Permission.READ_PRIVATE, CompactType.ASLP)).to.equal(true);
        expect(user.accountStatusDisplay()).to.equal('Active');
    });
    it('should create a Staff User with specific values through staff serializer (server-inactive -> pending)', () => {
        const data = {
            status: 'inactive',
        };
        const user = StaffUserSerializer.fromServer(data, { pageNum: 1 });

        expect(user).to.be.an.instanceof(StaffUser);
        expect(user.accountStatus).to.equal('pending');
        expect(user.accountStatusDisplay()).to.equal('Pending');
    });
    it('should create a Staff User with specific values through staff serializer (no permissions)', () => {
        const data = {};
        const user = StaffUserSerializer.fromServer(data);

        expect(user).to.be.an.instanceof(StaffUser);
        expect(user.hasPermission(Permission.READ_PRIVATE, CompactType.ASLP)).to.equal(false);
        expect(user.hasPermission(Permission.READ_SSN, CompactType.ASLP)).to.equal(false);
        expect(user.hasPermission(Permission.ADMIN, CompactType.ASLP)).to.equal(false);
        expect(user.hasPermission(Permission.READ_PRIVATE, CompactType.ASLP, 'co')).to.equal(false);
        expect(user.hasPermission(Permission.READ_SSN, CompactType.ASLP, 'co')).to.equal(false);
        expect(user.hasPermission(Permission.WRITE, CompactType.ASLP, 'co')).to.equal(false);
        expect(user.hasPermission(Permission.ADMIN, CompactType.ASLP, 'co')).to.equal(false);
    });
    it('should create a Staff User with specific values through staff serializer (state only permissions)', () => {
        const data = {
            permissions: {
                aslp: {
                    jurisdictions: {
                        co: {
                            actions: {
                                readPrivate: true,
                                readSSN: true,
                                write: true,
                                admin: true,
                            },
                        },
                    },
                },
            },
        };
        const user = StaffUserSerializer.fromServer(data);

        expect(user).to.be.an.instanceof(StaffUser);
        expect(user.hasPermission(Permission.READ_PRIVATE, CompactType.ASLP)).to.equal(false);
        expect(user.hasPermission(Permission.READ_SSN, CompactType.ASLP)).to.equal(false);
        expect(user.hasPermission(Permission.ADMIN, CompactType.ASLP)).to.equal(false);
        expect(user.hasPermission(Permission.READ_PRIVATE, CompactType.ASLP, 'co')).to.equal(true);
        expect(user.hasPermission(Permission.READ_SSN, CompactType.ASLP, 'co')).to.equal(true);
        expect(user.hasPermission(Permission.WRITE, CompactType.ASLP, 'co')).to.equal(true);
        expect(user.hasPermission(Permission.ADMIN, CompactType.ASLP, 'co')).to.equal(true);
    });
    it('should create a Staff User with specific values through staff serializer (compact level permissions)', () => {
        const data = {
            permissions: {
                aslp: {
                    actions: {
                        readPrivate: true,
                        readSSN: true,
                        admin: true,
                    },
                },
            },
        };
        const user = StaffUserSerializer.fromServer(data);

        expect(user).to.be.an.instanceof(StaffUser);
        expect(user.hasPermission(Permission.READ_PRIVATE, CompactType.ASLP)).to.equal(true);
        expect(user.hasPermission(Permission.READ_SSN, CompactType.ASLP)).to.equal(true);
        expect(user.hasPermission(Permission.ADMIN, CompactType.ASLP)).to.equal(true);
        expect(user.hasPermission(Permission.READ_PRIVATE, CompactType.ASLP, 'co')).to.equal(true);
        expect(user.hasPermission(Permission.READ_SSN, CompactType.ASLP, 'co')).to.equal(true);
        expect(user.hasPermission(Permission.WRITE, CompactType.ASLP, 'co')).to.equal(false);
        expect(user.hasPermission(Permission.ADMIN, CompactType.ASLP, 'co')).to.equal(true);
    });
    it('should prepare a Staff User for server request through serializer', () => {
        const data = {
            permissions: [
                {
                    compact: CompactType.ASLP,
                    isReadPrivate: true,
                    isReadSsn: true,
                    isAdmin: true,
                    states: [
                        {
                            abbrev: 'co',
                            isReadPrivate: true,
                            isReadSsn: true,
                            isWrite: true,
                            isAdmin: true,
                        },
                    ],
                },
            ],
            attributes: {
                email: 'test@example.com',
                firstName: 'Test',
                lastName: 'User',
            },
        };
        const requestData = StaffUserSerializer.toServer(data);

        expect(requestData).to.matchPattern({
            permissions: {
                [CompactType.ASLP]: {
                    actions: {
                        readPrivate: true,
                        readSSN: true,
                        admin: true,
                    },
                    jurisdictions: {
                        co: {
                            actions: {
                                readPrivate: true,
                                readSSN: true,
                                write: true,
                                admin: true,
                            },
                        },
                    },
                },
            },
            attributes: {
                email: data.attributes.email,
                givenName: data.attributes.firstName,
                familyName: data.attributes.lastName,
            },
        });
    });
});
