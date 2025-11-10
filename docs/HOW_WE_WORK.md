# COMPACT CONNECT CHARTER 

# Vision Statement
States use unique licensing systems that cannot easily, quickly, or securely share information, which limits access to healthcare and other licensed services across state lines through occupational licensure compacts. Compact Connect will provide a streamlined and secure route for compact users, state licensing staff, and members of the public to access safe and competent care.

# Project Values
## Security
Ensuring the confidentiality and security of personal information is an essential function of Compact Connect.
## Usability
When software is difficult to use, its impact decreases. Compact Connect will reduce barriers for system users by incorporating intuitive features.
## Longevity
Compacts are written such that they can adapt over time to changing regulatory and professional needs. Compact Connect will be created with this long-term view in mind.
## Public Service
Compacts primarily benefit three main stakeholder groups. Licensees using the compact enjoy a lower barrier to entry when seeking employment in remote states. Members of the public benefit from greater access to safe, diverse, and competent care in their state. State licensing boards become better equipped to protect the public through enhanced information sharing with other states. Compact Connect will serve all of these groups.

# Involved Organizations
## The Council of State Governments
The Council of State Governments (CSG) is the nation’s largest nonpartisan organization serving all three branches of state elected and appointed officials. Within CSG is housed the National Center for Interstate Compacts (NCIC). NCIC is working with compact stakeholders to guide the Compact Connect project.
## InspiringApps
InspiringApps designs and builds mobile, web, and custom apps and provides strategic business solutions and immersive experiences. InspiringApps is the development team working to build the Compact Connect software.
## Compact Commissions
Compact commissions are multistate organizations comprised of delegates from each compact member state. Compact commissions are key stakeholders in the Compact Connect project. Currently, three commissions are involved in the project:
Audiology and Speech Language Pathology Interstate Compact Commission
Counseling Compact Commission
Occupational Therapy Licensure Compact Commission
Compact Connect may later include additional occupational licensure compact commissions.

# How We Work
The Compact Connect team uses principles from Agile and Scrum. The team operates in two-week iterations called sprints. Each sprint begins with a planning meeting and ends with review and retrospective meetings.
## Sprint Events
### Daily Standup
The daily standup is a short meeting for the team to discuss what they are working on that day, any roadblocks that have come up, and other needed meetings for the day. Every ticket not in the “done” column is reviewed individually. Team members also mention upcoming absences of one or more days verbally in stand-up meetings the day prior.
Agenda:
- Major announcements
- Ticket review
- Additional discussion/planning
### Sprint Planning
The goal of the sprint planning meeting is to determine what items from the project backlog will be worked on during the next sprint. The attendees include anyone who will be working on a backlog item in the upcoming sprint and organizational supervisors. 
Agenda:
- Inspect unfinished tickets from prior sprint. Re-evaluate the tickets, including redefining any criteria necessary and changing the point value. Reassign them to the upcoming sprint or backlog.
- Pull in new tickets for upcoming sprint. Check to ensure user stories and acceptance criteria are clear and accurate.
- Discuss overarching goal of sprint (limit to one or two main priorities).
- Team approval of goal.
### Sprint Review
The goal of the sprint review meeting is to demonstrate what the team has accomplished over the last two weeks. The sprint review meeting attendees include developers, managers, and other stakeholder groups. Directors and designated representatives from compact commissions are especially encouraged to attend.
Agenda:
- Review goal and team progress towards goal.
- Look at finished tickets from sprint, particularly user interface tickets and features ready to demo.
- Provide brief summaries of research and technical tickets.
- Members of the call give feedback when possible.
- Briefly discuss upcoming sprint or any major announcements.
### Sprint Retrospective
The goal of the sprint retrospective is for the development team to reflect on what processes and procedures worked during the previous sprint and what needs to be improved. The attendees include those who contributed to the work of the previous sprint.
Agenda:
- Discuss action items from previous retrospective.
- What went well this sprint?
- What could be improved?
- Assign action items arising from the discussion.
### Backlog Refinement
Backlog refinement involves looking at the items in the backlog and ensuring they are correctly prioritized, clearly defined, and reasonably sized. The product manager will do some backlog refinement individually, including adding items discovered during user research and considering major priorities of the upcoming sprint. 
Backlog refinement meetings occur once a week (twice per sprint). The product manager and lead developer(s) attend this meeting to discuss the items in the backlog.

### Vendor pull requests

InspiringApps (IA) will work on their own fork of the repository. They will file a pull request against the Council of State Government (CSG) `development` branch upon completion of each feature within a sprint. All pull requests should be filed within one working day of the end of the sprint, e.g. if the sprint ends on a Thursday, any PRs for work completed within that sprint should be filed by the end of the day on Friday. Each pull request will be titled for the completed feature (e.g., `View disciplinary information`), and the description will link back to the story in the backlog, and should include an illustrative screenshot (where applicable).

CSG will review each pull request per the [code review process](CODE_REVIEW.md), to ensure that the work is compliance with the contract, and that the code adheres to best practices. CSG will make every effort to complete that code review within two working days of receiving it from InspiringApps, making that work the highest priority of the technical lead. Any requested changes etc. from CSG will be made in the spirit of collaboration and open discussion between CSG and IA, understanding that we are all learning together. When all issues raised in the code review have been addressed to CSG’s satisfaction, the pull request will be merged.

It is expected that each _sprint_ produces functional software sans test data, commented-out code, outdated tests, etc. Each user story should describe a specific need of a user archetype, and each sprint's pull requests should collectively implement one or more of these stories. Notably, while each pull request should follow stylistic best practices, it is possible that one pull request alone does not fully implement a user story (e.g., because the frontend and backend are offered as distinct pull requests). Therefore, since not all items in the [code review process](CODE_REVIEW.md) will apply to every pull request, CSG may selectively evaluate checklist items in pull request reviews and fill in the gaps at the end of the sprint. For example, CSG may choose to evaluate accessibility once per sprint and not for every pull request.

### Branch strategy

InspiringApps will use feature branches within their fork, and upon completion of that feature, will file a pull request from that branch to the `main` branch in CSG’s repo. CSG will periodically trigger deployments of features to the test, beta, and prod environments using git tags, pushed to (or created via) GitHub.

### InspiringApps workflow

InspiringApps developers will not necessarily keep their fork's `main` branch in sync with CSG's. To minimize risk of merge conflicts, they will branch directly from the CSG repository's `main` branch, rather than from that of the fork.

### API Design

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
