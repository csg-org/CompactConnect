//
//  mockOkta.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/27/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import sinon from 'sinon';

const okta = {
    handleAuthentication: sinon.stub(),
    isAuthenticated: sinon.stub().resolves(true),
    getAccessToken: sinon.stub().resolves('abc'),
    getUser: sinon.stub().resolves({}),
    logout: sinon.stub(),
};

export default okta;
