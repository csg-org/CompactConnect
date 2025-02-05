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
        let isMissingStep = false;
        let nextStep = 0;
        let i = 0;

        while (i < storeSteps.length && !isMissingStep) {
            const isStepFound = hasStep(i);

            if (isStepFound) {
                nextStep = i + 1;
                i += 1;
            } else {
                isMissingStep = true;
                nextStep = i;
            }
        }

        return nextStep;
    },
};
