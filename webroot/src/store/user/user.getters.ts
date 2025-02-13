//
//  user.getters.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

export default {
    state: (state: any) => state,
    currentCompact: (state: any) => state.currentCompact,
    getNextNeededPurchaseFlowStep: (state: any) => () => {
        const storeSteps = state.purchase.steps;
        const hasStep = (index) => (storeSteps.some((step) => (step.stepNum === index)));
        let nextStep = 0;

        while (hasStep(nextStep)) {
            nextStep += 1;
        }

        return nextStep;
    },
};
