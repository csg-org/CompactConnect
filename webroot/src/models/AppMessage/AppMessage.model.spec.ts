//
//  AppMessage.model.spec.ts
//  inHere
//
//  Created by InspiringApps on 4/12/20.
//  //  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { AppMessage, MessageTypes } from '@models/AppMessage/AppMessage.model';

describe('AppMessage model', () => {
    it('should create a AppMessage with expected defaults', () => {
        const appMessage = new AppMessage();

        expect(appMessage).to.be.an.instanceof(AppMessage);
        expect(appMessage.type).to.equal(MessageTypes.info);
        expect(appMessage.message).to.equal('');
    });
    it('should create an `info` message', () => {
        const messageOptions = {
            type: MessageTypes.info,
            message: 'Test error message',
        };
        const appMessage = new AppMessage(messageOptions);

        expect(appMessage.type).to.equal(MessageTypes.info);
        expect(appMessage.message).to.equal(messageOptions.message);
    });
    it('should create an `error` message', () => {
        const messageOptions = {
            type: MessageTypes.error,
            message: 'Test error message',
        };
        const appMessage = new AppMessage(messageOptions);

        expect(appMessage.type).to.equal(MessageTypes.error);
        expect(appMessage.message).to.equal(messageOptions.message);
    });
    it('should create a `success` message', () => {
        const messageOptions = {
            type: MessageTypes.success,
            message: 'Test success message',
        };
        const appMessage = new AppMessage(messageOptions);

        expect(appMessage.type).to.equal(MessageTypes.success);
        expect(appMessage.message).to.equal(messageOptions.message);
    });
});
