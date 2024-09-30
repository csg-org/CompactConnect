//
//  users.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 9/4/24.
//

export interface State {
    model: Array<any> | null;
    total: number;
    prevLastKey: string | null;
    lastKey: string | null;
    isLoading: boolean;
    error: any | null;
}

export const state: State = {
    model: null,
    total: 0,
    prevLastKey: null,
    lastKey: null,
    isLoading: false,
    error: null,
};
