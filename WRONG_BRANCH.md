# Branch from the CSG repository

If you're reading this file, you probably accidentally checked out the IA fork's `main` branch, instead of branching
directly from the CSG repo's `main` branch.

## CompactConnect branching strategy

The CompactConnect branching strategy includes only one trunk branch - the `main` branch in CSG's repository. This
repository is a fork of CSG's and we do not sync trunk branches here. Instead, each feature is developed on a feature
branch that is based directly from CSG's `main` branch.

## Creating a feature branch

To create a branch explicitly from the CSG repository's `main` branch, you can do the following:
```bash
# Add a CSG remote
git remote add csg git@github.com:csg-org/CompactConnect.git
# Create a branch explicitly tracking _their_ branch
git checkout -b feature-branch-name csg/main
```
