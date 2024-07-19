//
//  User.model.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/2020.
//

import { expect } from 'chai';
import { User, UserSerializer } from '@models/User/User.model';

describe('User model', () => {
    it('should create a User with expected defaults', () => {
        const user = new User();

        expect(user).to.be.an.instanceof(User);
        expect(user.id).to.equal(null);
        expect(user.email).to.equal(null);
        expect(user.firstName).to.equal(null);
        expect(user.lastName).to.equal(null);
        expect(user.getFullName()).to.equal('');
        expect(user.getInitials()).to.equal('');
    });
    it('should create a User with specific values', () => {
        const data = {
            id: 'id',
            email: 'email',
            firstName: 'firstName',
            lastName: 'lastName',
        };
        const user = new User(data);

        expect(user).to.be.an.instanceof(User);
        expect(user.id).to.equal(data.id);
        expect(user.email).to.equal(data.email);
        expect(user.firstName).to.equal(data.firstName);
        expect(user.lastName).to.equal(data.lastName);
        expect(user.getFullName()).to.equal(`${data.firstName} ${data.lastName}`);
        expect(user.getInitials()).to.equal('FL');
    });
    it('should create a User with specific values through serializer', () => {
        const data = {
            id: 'id',
            email: 'email',
            firstName: 'firstName',
            lastName: 'lastName',
        };
        const user = UserSerializer.fromServer(data);

        expect(user).to.be.an.instanceof(User);
        expect(user.id).to.equal(data.id);
        expect(user.email).to.equal(data.email);
        expect(user.firstName).to.equal(data.firstName);
        expect(user.lastName).to.equal(data.lastName);
        expect(user.getFullName()).to.equal(`${data.firstName} ${data.lastName}`);
        expect(user.getInitials()).to.equal('FL');
    });
});
