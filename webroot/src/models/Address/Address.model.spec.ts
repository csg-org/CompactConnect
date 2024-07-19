//
//  Address.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/8/2024.
//

import { expect } from 'chai';
import { Address, AddressSerializer } from '@models/Address/Address.model';
import { State } from '@models/State/State.model';

describe('Address model', () => {
    it('should create an Address with expected defaults', () => {
        const address = new Address();

        // Test field values
        expect(address).to.be.an.instanceof(Address);
        expect(address.id).to.equal(null);
        expect(address.street1).to.equal(null);
        expect(address.street2).to.equal(null);
        expect(address.city).to.equal(null);
        expect(address.state).to.be.an.instanceof(State);
        expect(address.zip).to.equal(null);
    });
    it('should create an Address with specific values', () => {
        const data = {
            id: 'test',
            street1: 'test',
            street2: 'test',
            city: 'test',
            state: new State(),
            zip: 'test',
        };
        const address = new Address(data);

        // Test field values
        expect(address).to.be.an.instanceof(Address);
        expect(address.id).to.equal(data.id);
        expect(address.street1).to.equal(data.street1);
        expect(address.street2).to.equal(data.street2);
        expect(address.city).to.equal(data.city);
        expect(address.state).to.be.an.instanceof(State);
        expect(address.zip).to.equal(data.zip);
    });
    it('should create an Address with specific values through serializer', () => {
        const data = {
            id: 'test-id',
            street1: 'test-street1',
            street2: 'test-stree2',
            city: 'test-city',
            state: new State(),
            zip: 'test-zip',
        };
        const address = AddressSerializer.fromServer(data);

        // Test field values
        expect(address).to.be.an.instanceof(Address);
        expect(address.id).to.equal(data.id);
        expect(address.street1).to.equal(data.street1);
        expect(address.street2).to.equal(data.street2);
        expect(address.city).to.equal(data.city);
        expect(address.state).to.be.an.instanceof(State);
        expect(address.zip).to.equal(data.zip);
    });
    it('should serialize an Address for transmission to server with all values', () => {
        const address = AddressSerializer.fromServer({
            id: 'test-id',
            street1: 'test-street1',
            street2: 'test-street2',
            city: 'test-city',
            state: new State({ abbrev: 'test-state' }),
            zip: 'test-zip',
        });
        const transmit = AddressSerializer.toServer(address);

        expect(transmit.street1).to.equal(address.street1);
        expect(transmit.street2).to.equal(address.street2);
        expect(transmit.city).to.equal(address.city);
        expect(transmit.state).to.equal(address.state.abbrev);
        expect(transmit.zip).to.equal(address.zip);
    });
    it('should serialize an Address for transmission to server with missing values', () => {
        const address = AddressSerializer.fromServer({});
        const transmit = AddressSerializer.toServer(address);

        expect(transmit.street1).to.equal(undefined);
        expect(transmit.street2).to.equal(undefined);
        expect(transmit.city).to.equal(undefined);
        expect(transmit.state).to.equal(undefined);
        expect(transmit.zip).to.equal(undefined);
    });
});
