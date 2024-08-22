//
//  router.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import guards from '@router/_guards';
import store from '@/store';

const chaiMatchPattern = require('chai-match-pattern');
const chai = require('chai').use(chaiMatchPattern);

const { expect } = chai;

describe('Router Guards', () => {
    it('should successfully return authentication guard', () => {
        // authGuard() has special handling for test-runner - expect `true` result here.
        const result = guards.authGuard();

        expect(result).to.equal(true);
    });
    it('should successfully return no-authentication guard (default)', () => {
        const result = guards.noAuthGuard();

        expect(result).to.equal(true);
    });
    it('should successfully return no-authentication guard (is logged in)', async () => {
        await store.dispatch('user/loginSuccess');

        const result = guards.noAuthGuard();

        expect(result).to.matchPattern({ name: 'Home' });
    });
});
