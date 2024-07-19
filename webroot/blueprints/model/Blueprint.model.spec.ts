//
//  Blueprint.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on MM/DD/YYYY.
//

import { expect } from 'chai';
import { Blueprint } from '@models/Blueprint/Blueprint.model';

describe('Blueprint model', () => {
    it('should create a Blueprint', () => {
        const blueprint = new Blueprint();

        expect(blueprint).to.be.an.instanceof(Blueprint);
    });
});
