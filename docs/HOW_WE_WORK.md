# How We Work

## Vendor pull requests

Just a test...take2

InspiringApps (IA) will work on their own fork of the repository. They will file a pull request against the Council of State Government (CSG) `development` branch upon completion of each feature within a sprint. All pull requests should be filed within one working day of the end of the sprint, e.g. if the sprint ends on a Thursday, any PRs for work completed within that sprint should be filed by the end of the day on Friday. Each pull request will be titled for the completed feature (e.g., `View disciplinary information`), and the description will link back to the story in the backlog, and should include an illustrative screenshot (where applicable).

CSG will review each pull request per the [code review process](CODE_REVIEW.md), to ensure that the work is compliance with the contract, and that the code adheres to best practices. CSG will make every effort to complete that code review within two working days of receiving it from InspiringApps, making that work the highest priority of the technical lead. Any requested changes etc. from CSG will be made in the spirit of collaboration and open discussion between CSG and IA, understanding that we are all learning together. When all issues raised in the code review have been addressed to CSG’s satisfaction, the pull request will be merged.

It is expected that each _sprint_ produces functional software sans test data, commented-out code, outdated tests, etc. Each user story should describe a specific need of a user archetype, and each sprint's pull requests should collectively implement one or more of these stories. Notably, while each pull request should follow stylistic best practices, it is possible that one pull request alone does not fully implement a user story (e.g., because the frontend and backend are offered as distinct pull requests). Therefore, since not all items in the [code review process](CODE_REVIEW.md) will apply to every pull request, CSG may selectively evaluate checklist items in pull request reviews and fill in the gaps at the end of the sprint. For example, CSG may choose to evaluate accessibility once per sprint and not for every pull request.

## Branch strategy

InspiringApps will use feature branches within their fork, and upon completion of that feature, will file a pull request from that branch to the `development` branch in CSG’s repo. CSG will periodically merge the `development` branch to `main`, through a process and at a frequency to be determined.

## API Design

As this project progresses, we will be building out a RESTful API to facilitate compact-member board IT systems
integrating with CompactConnect. In order to minimize level of effort for systems integration with our API, we will
do our best to build an API that:

- is secure;
- is intuitive to technical staff;
- is sensible for board staff to use; and
- meets the needs of boards across the compacts using this system.

To that end, we will establish our design principles here that aim to best meet those goals. Note that these are
_principles_, not hard rules. These are intended to help us to meet our API goals, by establishing common stated
priorities, not to constrain our options. That said, here are the principles we will use to guide us:

- We will respect REST API design conventions, as they are described [here](https://restfulapi.net/).
- Once we release a major API version, we will support that api, making only non-breaking changes. Should breaking
  changes be necessary we will incorporate those updates into a new major version and work with clients to gracefully
  migrate to the new major version before deprecating the old major version.
- We will build the API to create a uniform resource naming system that is self-consistent.
- We will design the API to be easy to use correctly and difficult to misuse.
- We will design the API to be idempotent, where applicable.
- Underlying implementation details are secondary to a clean API.
