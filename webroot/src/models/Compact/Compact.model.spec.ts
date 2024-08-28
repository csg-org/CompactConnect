//
//  Compact.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/27/2024.
//

import { expect } from 'chai';
import { Compact } from '@models/Compact/Compact.model';

describe('Compact model', () => {
    it('should create a Compact', () => {
        const compact = new Compact();

        expect(compact).to.be.an.instanceof(Compact);
    });
});
