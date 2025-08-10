# UV-bump

Bump pyproject.toml dependency minimum versions to latest feasible versions.

WARNING: this tool is provided as-is and doesn't come with warranty.
Please make sure your code has been backed up and/or version controlled in case something goes wrong.


## Howto

Within your project, ensure that it is clean. That is:

1. your `uv.lock` file is up to date and commited
2. your `.venv` is up to date

Run `uv sync --all-extras` if you are unsure, and commit your lock file if any changes.

Proceed by installing the tool and running it:

```bash
uvx uv-bump
```

Alternatively, if you want to add uv-bump to your development dependencies:
```bash
uv add --dev uv-bump
uv-bump
```
UV-bump will run `uv sync`, which updates the packages in your virtual environment and your `uv.lock` file, and in addition updates `pyproject.toml` by bumping all minimum bounds to the version installed.
Review the changes, and when happy, commit.

UV-bump will respect your currently set version pins and bounds.
For example, if you specify `polars==1.20.0`, Polars won't be updated, although newer versions are available.
Similarly, if you set `plotly>=5.0,<6.0` version 6 of Plotly will not be selected.
To make these available, change the specifications to use `>=` without an upper bound.
If you find that a particular package upgrade is difficult and warrants more attention, edit `pyproject.toml` to add an upper bound, and re-run UV-bump.
In this way, you can keep up to date on all the non-breaking changes whilst holding back bigger updates if needed.

## Why uv-bump?
UV-bump is a tool help application developers keep up to date on their dependencies.
For library developers, the `pyproject.toml` dependency specifications are usually set as wide as possible.
However, for application developers, this is not desirable, and ideally versions are being kept up-to-date to incorporate bug fixes and, if desired, feature upgrades.
Although `uv sync --upgrade` will up the versions in your `uv.lock` file, it won't touch the `pyproject.toml` file.
This causes the dependency specifications to lag reality.
For example, say you use package X version Y, and specify "PackageX>=Y".
Over time, a new version, Z, comes out.
The `uv.lock` file is updated with `uv sync --upgrade`, and you end up using the new version, and start using some of the new features.
Effectively, `pyproject.toml` is now outdated, your application won't work any longer with version `Y`, but only version `Z`, which can cause problems down the road. 


## FAQ

Q1. Help, UV-bump does not select the latest version?

A1. UV-bump uses UV to resolve package requirements. It may well be that amongst your dependencies one or more are holding
   your dependency back.


Q2. will UV add native support for this functionality?

A2. See the issue tracker: https://github.com/astral-sh/uv/issues/6794


Q3. Can I see which of my dependencies are outdated?

A3. `uv pip list --outdated`. This does not, per Q1, mean that they can actually all be updated to the latest version.
