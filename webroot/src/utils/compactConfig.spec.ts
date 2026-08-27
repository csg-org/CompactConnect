//
//  compactConfig.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/18/2026.
//

import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { AppModes, AppGroupModes } from '@/app.config';
import { config as envConfig } from '@plugins/EnvConfig/envConfig.plugin';
import {
    CompactType,
    compactSetups,
    appModeGroups,
    getCompactSetup,
    getAppModeForCompact,
    getAppGroupModeForAppMode,
    getEncumberConfigLicense,
    getEncumberConfigPrivilege
} from '@utils/compactConfig';

chai.use(chaiMatchPattern);

const { expect } = chai;

describe('compactConfig utils', () => {
    afterEach(() => {
        envConfig.isAppProduction = false;
    });

    it('should successfully include every compact type in compactSetups', () => {
        expect(Object.keys(compactSetups)).to.matchPattern([
            CompactType.ASLP,
            CompactType.OT,
            CompactType.COUNSELING,
            CompactType.COSMETOLOGY,
            CompactType.SOCIAL_WORK,
        ]);
    });
    it('should successfully map each compact to its app mode', () => {
        expect(getAppModeForCompact(CompactType.ASLP)).to.equal(AppModes.JCC);
        expect(getAppModeForCompact(CompactType.OT)).to.equal(AppModes.JCC);
        expect(getAppModeForCompact(CompactType.COUNSELING)).to.equal(AppModes.JCC);
        expect(getAppModeForCompact(CompactType.COSMETOLOGY)).to.equal(AppModes.COSMETOLOGY);
        expect(getAppModeForCompact(CompactType.SOCIAL_WORK)).to.equal(AppModes.SOCIAL_WORK);
    });
    it('should successfully fall back to jcc for an unknown compact type', () => {
        expect(getAppModeForCompact('not-a-compact')).to.equal(AppModes.JCC);
        expect(getAppModeForCompact(null)).to.equal(AppModes.JCC);
        expect(getAppModeForCompact(undefined)).to.equal(AppModes.JCC);
    });
    it('should successfully return compact setup for a known type and null for unknown', () => {
        expect(getCompactSetup(CompactType.ASLP)).to.matchPattern({
            type: CompactType.ASLP,
            appMode: AppModes.JCC,
            isEnabled: Function,
        });
        expect(getCompactSetup('not-a-compact')).to.equal(null);
        expect(getCompactSetup(null)).to.equal(null);
    });
    it('should successfully map each app mode to its app group mode', () => {
        expect(appModeGroups).to.matchPattern({
            [AppModes.JCC]: AppGroupModes.PRIVILEGE_PURCHASE,
            [AppModes.COSMETOLOGY]: AppGroupModes.MULTI_STATE,
            [AppModes.SOCIAL_WORK]: AppGroupModes.MULTI_STATE,
        });
        expect(getAppGroupModeForAppMode(AppModes.JCC)).to.equal(AppGroupModes.PRIVILEGE_PURCHASE);
        expect(getAppGroupModeForAppMode(AppModes.COSMETOLOGY)).to.equal(AppGroupModes.MULTI_STATE);
        expect(getAppGroupModeForAppMode(AppModes.SOCIAL_WORK)).to.equal(AppGroupModes.MULTI_STATE);
    });
    it('should successfully return null for an unknown app mode group lookup', () => {
        expect(getAppGroupModeForAppMode('not-an-app-mode' as AppModes)).to.equal(null);
        expect(getAppGroupModeForAppMode(null)).to.equal(null);
    });

    it('should successfully enable jcc compacts in all environments', () => {
        envConfig.isAppProduction = true;

        expect(compactSetups[CompactType.ASLP].isEnabled()).to.equal(true);
        expect(compactSetups[CompactType.OT].isEnabled()).to.equal(true);
        expect(compactSetups[CompactType.COUNSELING].isEnabled()).to.equal(true);
        expect(compactSetups[CompactType.COSMETOLOGY].isEnabled()).to.equal(true);
    });
    it('should successfully gate socw to non-production environments', () => {
        expect(compactSetups[CompactType.SOCIAL_WORK].isEnabled()).to.equal(true);

        envConfig.isAppProduction = true;

        expect(compactSetups[CompactType.SOCIAL_WORK].isEnabled()).to.equal(false);
    });
    it('should successfully return license encumber config per app mode', () => {
        expect(getEncumberConfigLicense(AppModes.JCC).disciplineTypes).to.include('surrender of license');
        expect(getEncumberConfigLicense(AppModes.JCC).npdbTypes).to.include('Misconduct or Abuse');

        expect(getEncumberConfigLicense(AppModes.COSMETOLOGY).disciplineTypes).to.eql([
            'suspension',
            'revocation',
            'surrender of license',
        ]);
        expect(getEncumberConfigLicense(AppModes.COSMETOLOGY).npdbTypes).to.eql([
            'fraud',
            'consumer harm',
            'other',
        ]);

        expect(getEncumberConfigLicense(AppModes.SOCIAL_WORK).disciplineTypes).to.include('surrender of license');
        expect(getEncumberConfigLicense(AppModes.SOCIAL_WORK).npdbTypes).to.include('Conflict of Interest');
    });
    it('should successfully return privilege encumber config per app mode', () => {
        expect(getEncumberConfigPrivilege(AppModes.JCC).disciplineTypes).to.include('surrender of privilege');
        expect(getEncumberConfigPrivilege(AppModes.COSMETOLOGY).disciplineTypes).to.eql([
            'suspension',
            'revocation',
            'surrender of privilege',
        ]);
        expect(getEncumberConfigPrivilege(AppModes.SOCIAL_WORK).disciplineTypes).to.include('surrender of privilege');
        expect(getEncumberConfigPrivilege(AppModes.SOCIAL_WORK).npdbTypes).to.include(
            'Improper Prescribing, Dispensing, Administering Medication/Drug Violation'
        );
    });
    it('should successfully return empty encumber config for an unrecognized app mode', () => {
        expect(getEncumberConfigLicense('not-an-app-mode' as AppModes)).to.matchPattern({
            disciplineTypes: [],
            npdbTypes: [],
        });
        expect(getEncumberConfigPrivilege('not-an-app-mode' as AppModes)).to.matchPattern({
            disciplineTypes: [],
            npdbTypes: [],
        });
    });
});
