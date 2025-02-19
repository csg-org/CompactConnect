#!/usr/bin/env python3
"""
Script to search this project for Python and NodeJS dependencies, identify their licenses, and write the results to a
CSV file.

Note: Some dependencies don't make finding their license information very easy (shame, Python devs!), so this script does its best
to mine PyPi and GitHub for license data. It does not find all licenses. The resulting CSV will have some NOASSERTION licenses,
which will need manual search and entry.

This script is intended to be run from the root of the project.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import re
import subprocess
from abc import ABC, abstractmethod
from collections.abc import Iterable
from urllib.parse import urlparse

from requests import Session
from requests.adapters import HTTPAdapter
from urllib3 import Retry

logger = logging.getLogger(__name__)


# We can exceed the rate limit for the GitHub API if we're not careful, so we'll use a retry strategy with a
# conservative backoff factor
session = Session()
retry = Retry(
    total=5,
    read=5,
    connect=5,
    backoff_factor=3,
    status_forcelist=(500, 502, 504, 403, 429),
)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)


class Dependency(ABC):
    def __init__(self, name: str, version: str, location: str, language: str):
        self.name = name
        self.version = version
        self.language = language
        self.location: set[str] = {location}
        self.package_url: str | None = None

        self._licensee = None
        self.repo_url: str | None = None

    @property
    def license(self) -> str | None:
        return self._license

    @license.setter
    def license(self, value: str | None):
        """
        Perform some data consistency corrections as the value is set
        """
        # We'll stick with the SPDX license short identifiers.
        if isinstance(value, str):
            if value.lower() == 'mit license':
                value = 'MIT'
            if value.lower() in ('apache license 2.0', 'apache 2.0'):
                value = 'Apache-2.0'
            if value.lower() == 'unknown':
                value = None
        elif value is not None:
            raise ValueError(f'License must be a string or None: {value}')
        self._license = value

    @classmethod
    @abstractmethod
    def load_dependencies(cls, file_path: str) -> list[Dependency]:
        pass

    @abstractmethod
    def get_license_info(self):
        pass

    @staticmethod
    def _get_github_license(github_url: str) -> str | None:
        """Get license information from a GitHub repository."""
        logger.info('Fetching GitHub license for %s', github_url)
        # Convert full GitHub URL to API URL
        # From: https://github.com/owner/repo
        # To: https://api.github.com/repos/owner/repo
        parsed = urlparse(github_url)
        if parsed.netloc != 'github.com':
            raise ValueError(f'Not a GitHub URL: {github_url}')

        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            raise ValueError(f'Invalid GitHub URL format: {github_url}')

        owner, repo = path_parts[:2]
        api_url = f'https://api.github.com/repos/{owner}/{repo}'

        try:
            response = session.get(api_url)
            response.raise_for_status()
            repo_data = response.json()
            return repo_data.get('license', {}).get('spdx_id')
        except Exception as e:  # noqa: BLE001
            logger.error('Error getting GitHub license for %s: %s', github_url, e, exc_info=e)
            raise


class NodeJSDependency(Dependency):
    def __init__(self, name: str, version: str, location: str):
        super().__init__(name, version, location, 'NodeJS')
        self.package_url = f'https://www.npmjs.com/package/{name}'

    @classmethod
    def load_dependencies(cls, file_path: str) -> list[Dependency]:
        """Parse package.json to get direct dependencies."""
        deps = []

        with open(file_path) as f:
            data = json.load(f)

        # Regular dependencies
        if 'dependencies' in data:
            for name, version in data['dependencies'].items():
                # Strip version prefix characters
                clean_version = re.sub(r'^[~^]', '', version)
                deps.append(cls(name, clean_version, os.path.dirname(file_path)))

        # Dev dependencies
        if 'devDependencies' in data:
            for name, version in data['devDependencies'].items():
                clean_version = re.sub(r'^[~^]', '', version)
                deps.append(cls(name, clean_version, os.path.dirname(file_path)))

        return deps

    def get_license_info(self):
        """Get license information for an NPM package."""
        logger.info('Getting license information for NPM package %s', self.name)
        result = subprocess.run(  # noqa: S603
            ['yarn', 'info', f'{self.name}@{self.version}', '--json'],  # noqa: S607
            capture_output=True,
            text=True,
            cwd=list(self.location)[0],
        )
        if result.returncode != 0:
            logger.error('Error getting license for NPM package %s: %s', self.name, result.stderr)
            raise RuntimeError(f'Error getting license for NPM package {self.name}: {result.stderr}')
        data = json.loads(result.stdout)['data']
        license_name = data['license']

        repo_url = None
        repo_url = data.get('repository', {}).get('url')
        # If they don't list a repository, we'll use the homepage as a fallback
        if not repo_url:
            repo_url = data.get('homepage', '').split('#')[0]

        # As a last resort, point to npmjs.com https://www.npmjs.com/package/@usewaypoint/email-builder
        if not repo_url:
            repo_url = f'https://www.npmjs.com/package/{self.name}'

        # Convert funky git URLs to https URL if it's for GitHub
        if 'github.com' in repo_url:
            repo_url = repo_url.replace('git+', '').replace('.git', '').replace('ssh://git@', 'https://')

        self.license = license_name
        self.repo_url = repo_url


class PythonDependency(Dependency):
    def __init__(self, name: str, version: str, location: str):
        super().__init__(name, version, location, 'Python')
        self.package_url = f'https://pypi.org/project/{name}'

    @classmethod
    def load_dependencies(cls, file_path: str) -> list[Dependency]:
        """Parse requirements.txt to get direct dependencies."""
        deps = []
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith(('#', '-r')):
                    continue

                # Parse package name and version
                # Handle different formats like:
                # package==1.0.0
                # package>=1.0.0
                # package>=1.0.0,<2.0.0
                # package[option]>=1.0.0
                parts = re.split(r'[=<>\[\]]', line)[0].strip()
                version_match = re.search(r'[=<>]=\s*([\d.]+)', line)
                version = version_match.group(1) if version_match else 'latest'

                deps.append(cls(parts, version, os.path.dirname(file_path)))

        return deps

    def get_license_info(self):
        """Get license information for a Python package."""
        logger.info('Getting license information for Python package %s', self.name)
        result = subprocess.run(['pip', 'show', self.name], capture_output=True, text=True)  # noqa: S607 S603

        if result.returncode != 0:
            logger.error('Error getting license for Python package %s: %s', self.name, result.stderr)
            raise RuntimeError(f'Error getting license for Python package {self.name}: {result.stderr}')

        # Extract license from pip show output
        license_match = re.search(r'License: (.+)', result.stdout)
        self.license = license_match.group(1) if license_match else None

        # Try to get the home page as a potential license URL
        home_page_match = re.search(r'Home-page: (.+)', result.stdout)
        self.repo_url = home_page_match.group(1) if home_page_match else None

        # A bunch of pip packages don't include their license in pip metadata, so we'll go mining for that info
        # via PyPi and GitHub

        # If we don't get a license and url from pip metadata, we'll go mining for it on PyPI
        if not self.license or not self.repo_url:
            self.repo_url, self.license = self._get_pypi_info()

        # If we still don't have a license, we'll go mining for it on GitHub
        if not self.license:
            self.license = self._get_github_license(self.repo_url)

    def _get_pypi_info(self) -> tuple[str, str | None]:
        """Get package information from PyPI when pip metadata is insufficient."""
        logger.info('Fetching PyPI info for %s', self.name)
        response = session.get(f'https://pypi.org/pypi/{self.name}/json')
        response.raise_for_status()
        data = response.json()

        # Get repository URL from project URLs
        repo_url = None
        license_name = data['info'].get('license')

        pypi_info = data['info']
        if license_name is not None:
            # If we found a license, we'll take any URL we can find
            repo_url = self._find_url_in_pypi_info(pypi_info, github_only=False)
        else:
            # If we still haven't found a license, we'll try to find a GitHub URL so we can
            # look for a license there.
            repo_url = self._find_url_in_pypi_info(pypi_info, github_only=True)

        if not repo_url:
            raise RuntimeError(f'No suitable URL found for {self.name}')

        return repo_url, license_name

    def _find_url_in_pypi_info(self, pypi_info: dict, github_only: bool = False) -> str:
        """
        URLs or can be found under a bunch of different names and places in PyPI info
        """
        project_urls = pypi_info.get('project_urls', {})
        for key in [
            'Code',
            'code',
            'GitHub',
            'Github',
            'github',
            'Repository',
            'repository',
            'Source Code',
            'Source code',
            'source code',
            'Source',
            'source',
            'Homepage',
            'homepage',
        ]:
            if key in project_urls and ('github.com' in project_urls[key] or not github_only):
                return project_urls[key]

        # Fallback to homepage
        homepage = pypi_info.get('home_page')
        if homepage and ('github.com' in homepage or not github_only):
            return homepage
        raise RuntimeError(f'No suitable URL found for {self.name}')


def find_dependency_files() -> tuple[list[str], list[str]]:
    """Find all package.json and requirements.txt files in the project."""
    package_jsons = []
    requirements_txts = []

    for root, dirs, files in os.walk('.'):
        # Filter for some exclude patterns
        dirs[:] = [d for d in dirs if d not in ['node_modules', 'cdk.out', '.git']]

        for file in files:
            if file == 'package.json':
                package_jsons.append(os.path.join(root, file))
            elif file in ['requirements.txt', 'requirements-dev.txt']:
                requirements_txts.append(os.path.join(root, file))

    return package_jsons, requirements_txts


def deduplicate_dependencies(deps: Iterable[Dependency]) -> Iterable[Dependency]:
    """Deduplicate dependencies by name, keeping the most specific version."""
    unique_deps: dict[str, Dependency] = {}

    for dep in deps:
        key = f'{dep.language}:{dep.name}'
        if key not in unique_deps:
            unique_deps[key] = dep
        else:
            existing = unique_deps[key]
            # If the existing version is 'latest', prefer the specific version
            if existing.version == 'latest' and dep.version != 'latest':
                unique_deps[key] = dep
            existing.location |= dep.location

    return unique_deps.values()


def main():
    logger.info('Starting dependency analysis')

    # Find all dependency files
    logger.info('Finding dependency files')
    package_jsons, requirements_txts = find_dependency_files()

    # Parse all dependencies
    all_deps: list[Dependency] = []

    # Parse NodeJS dependencies
    logger.info('Parsing NodeJS dependencies')
    for package_json in package_jsons:
        logger.info('Parsing NodeJS dependencies from %s', package_json)
        deps = NodeJSDependency.load_dependencies(package_json)
        all_deps.extend(deps)

    # Parse Python dependencies
    logger.info('Parsing Python dependencies')
    for requirements_txt in requirements_txts:
        logger.info('Parsing Python dependencies from %s', requirements_txt)
        deps = PythonDependency.load_dependencies(requirements_txt)
        all_deps.extend(deps)

    # Deduplicate dependencies
    unique_deps = deduplicate_dependencies(all_deps)

    # Get license information for each dependency
    logger.info('Getting license information for each dependency')
    for dep in unique_deps:
        dep.get_license_info()

    # Write results to CSV
    logger.info('Writing results to CSV')
    with open('dependency_licenses.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Package Name', 'Version', 'Language', 'License', 'Package URL', 'Repo URL', 'Location'])

        # an Unknown license should never appear here, since we raise an exception if we don't find a license, but
        # we'll add a value that's easy to check for in case of a bug.
        for dep in sorted(unique_deps, key=lambda x: (x.language, x.license or 'Unknown', x.name.lower(), x.version)):
            writer.writerow(
                [
                    dep.name,
                    dep.version,
                    dep.language,
                    dep.license or 'Unknown',
                    dep.package_url or 'N/A',
                    dep.repo_url or 'N/A',
                    ':'.join(dep.location),
                ]
            )
    logger.info('Done!')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    main()
