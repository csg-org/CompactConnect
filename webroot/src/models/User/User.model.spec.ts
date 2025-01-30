//
//  User.model.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/2020.
//
import { User } from '@models/User/User.model';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import i18n from '@/i18n';
import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';

chai.use(chaiMatchPattern);

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
        expect(user.firstName).to.equal(null);
        expect(user.lastName).to.equal(null);
        expect(user.accountStatus).to.equal('');
        expect(user.getFullName()).to.equal('');
        expect(user.getInitials()).to.equal('');
        expect(user.accountStatusDisplay()).to.equal('');
    });
    it('should create a User with specific values', () => {
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
        expect(user.firstName).to.equal(data.firstName);
        expect(user.lastName).to.equal(data.lastName);
        expect(user.accountStatus).to.equal(data.accountStatus);
        expect(user.getFullName()).to.equal(`${data.firstName} ${data.lastName}`);
        expect(user.getInitials()).to.equal('FL');
        expect(user.accountStatusDisplay()).to.equal('Active');
    });
});
