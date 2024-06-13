//
//  sorting.state.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/22/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

export enum SortDirection {
    asc = 'asc',
    desc = 'desc'
}

export interface State {
    sortingMap: object;
}

export const state: State = {
    sortingMap: {}
};
