# How We Work

## Vendor pull requests

InspiringApps (IA) will work on their own fork of the repository. They will file a pull request against the Council of State Government (CSG) `development` branch upon completion of each feature within a sprint. All pull requests should be filed within one working day of the end of the sprint, e.g. if the sprint ends on a Thursday, any PRs for work completed within that sprint should be filed by the end of the day on Friday. Each pull request will be titled for the completed feature (e.g., `View disciplinary information`), and the description will link back to the story in the backlog, and should include an illustrative screenshot (where applicable).

CSG will review each pull request per the [code review process](CODE_REVIEW.md), to ensure that the work is compliance with the contract, and that the code adheres to best practices. CSG will make every effort to complete that code review within two working days of receiving it from InspiringApps, making that work the highest priority of the technical lead. Any requested changes etc. from CSG will be made in the spirit of collaboration and open discussion between CSG and IA, understanding that we are all learning together. When all issues raised in the code review have been addressed to CSG’s satisfaction, the pull request will be merged.

It is expected that each sprint produces functional software sans test data, commented-out code, outdated tests, etc. Each user story should describe a specific need of a user archetype, and each sprint's pull requests should collectively implement one or more of these stories. Since not all items in the [code review process](CODE_REVIEW.md) will apply to every pull request, CSG may selectively evaluate checklist items in pull request reviews and fill in the gaps at the end of the sprint. For example, CSG may choose to evaluate accessibility once per sprint and not for every pull request.

## Branch strategy

InspiringApps will use feature branches within their fork, and upon completion of that feature, will file a pull request from that branch to the `development` branch in CSG’s repo. CSG will periodically merge the `development` branch to `main`, through a process and at a frequency to be determined.
