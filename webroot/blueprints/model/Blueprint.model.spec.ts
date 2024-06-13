//
//  Blueprint.model.spec.ts
//  <the-app-name>
//
//  Created by InspiringApps on MM/DD/YY.
//  Copyright © 2024. <the-customer-name>. All rights reserved.
//

import { expect } from 'chai';
import { Blueprint } from '@models/Blueprint/Blueprint.model';

describe('Blueprint model', () => {
    it('should create a Blueprint', () => {
        const blueprint = new Blueprint();

        expect(blueprint).to.be.an.instanceof(Blueprint);
    });
});
