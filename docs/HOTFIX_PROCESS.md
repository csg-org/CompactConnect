# CompactConnect Hotfix Deployment Process

## Overview

This document outlines the process for deploying critical hotfixes to the production environment while maintaining the 
integrity of our Git Flow workflow and preventing merge conflicts with ongoing development work.

This project has both a development and main branch. Commits to the development branch trigger deployments to the test 
environment. Commits to the main branch trigger deployments to the beta and production environments. Generally, changes
are first merged into development, then merged into main once a Sprint. In the case of hotfixes, critical changes may 
need to be merged into main and deployed to production first. The hotfix branch may then be merged into development to
keep main and development in sync.

## Hotfix Process
### 1. Create Hotfix Branch from Main Branch

```bash
# Ensure you have the latest main branch
git checkout main
git pull origin main

# Create hotfix branch from main (production state)
git checkout -b hotfix/<issue-description>

# Example:
git checkout -b hotfix/fix-authentication-timeout
```

### 2. Implement the Fix

- Make **minimal changes** - only what's necessary to resolve the critical issue
- Avoid refactoring, feature additions, or unrelated improvements
- Test locally to ensure the fix works and no regressions are introduced

### 3. Pull Request into Main Branch

- Push change up to origin
- Open Pull Request to merge hotfix branch into main branch
- Have member with write access to repo perform review
- Merge into main using **Merge commit** (NOT SQUASH OR REBASE)

NOTE: The depth of hotfix code reviews should vary based on urgency. Follow-up PRs can be used to address minor feedback. 
For example, for security-related hotfixes, CSG may choose to review only for significant concerns that could impact 
security or functionality, and defer other changes (e.g., style, tests, documentation) to a follow-up PR under SOP.

```bash
# Push hotfix branch
git push origin hotfix/<issue-description>

# Create pull request targeting main branch
# Request expedited review from team leads
# Merge after approval using a merge commit
```

### 4. Monitor Deployment

- Monitor the AWS CodePipeline execution
- Watch for any deployment failures
- Monitor application metrics and logs
- Verify the fix is working in production


### 5. Pull Request into Development

- Open Pull Request to merge same hotfix branch into development branch
- Merge into development using **Merge commit** (NOT SQUASH OR REBASE)
- verify hotfix is successfully deployed to development environment.

### 6. Delete Hotfix Branch

- delete both local and remote hotfix branch

## Emergency Hotfix Checklist

- [ ] Issue confirmed in production
- [ ] Hotfix branch created from main
- [ ] Minimal changes implemented
- [ ] Local testing completed
- [ ] Hotfix merged to main
- [ ] Production deployment monitored
- [ ] Fix verified in production
- [ ] Hotfix merged back to development
- [ ] Branches cleaned up
- [ ] Post-mortem scheduled (if needed)
