//
//  cypress.config.js
//  InspiringApps modules
//
//  Created by InspiringApps on 04/27/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { defineConfig } from 'cypress'

export default defineConfig({
  defaultCommandTimeout: 10000,
  fixturesFolder: 'tests/e2e/fixtures',
  screenshotsFolder: 'tests/e2e/screenshots',
  videosFolder: 'tests/e2e/videos',
  browsers: [
    {
      displayName: 'Edge',
      family: 'chromium',
      majorVersion: 83,
      name: 'edge',
      path: '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
      version: '83.0.478.54',
    },
  ],
  e2e: {
    specPattern: 'tests/e2e/specs/**/*.cy.{js,jsx,ts,tsx}',
    supportFile: 'tests/e2e/support/index.js',
  },
})
